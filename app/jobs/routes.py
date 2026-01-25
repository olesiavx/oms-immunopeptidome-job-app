from io import BytesIO
from flask import render_template, redirect, url_for, flash, request, abort, jsonify, send_file, current_app 
from flask_login import login_required, current_user
from . import jobs_bp
from .forms import (
    NewJobForm, SearchConfigForm, ValidationConfigForm,
    RawFileForm, DatabaseRequestForm, MicroproteomeRoundForm,
    AssignJobForm, UpdateStatusForm
)
from app.jobs.wizard_tree import WizardTree
from app.jobs.wizard_service import WizardSessionService
from .wizard_forms import NewJobWizardForm
from ..extensions import db
from ..models import (
    Job, JobEvent, JobStatus,
    SearchConfig, ValidationConfig,
    JobRawFile, DatabaseRequest, MicroproteomeRound,
    User, Role, ProjectType, DatabaseTier,
    MSMode, TMTLabelType, SearchEnginesMode,
    Project, JobAssignment
)
from pathlib import Path
from ..forms import CSRFOnlyForm
import io

from .wizard_tree import get_public_state, get_node_for_path

def _wizard_service() -> WizardSessionService:
    tree_path = Path(current_app.root_path) / "jobs" / "config" / "wizard_tree.json"
    tree = WizardTree.from_json_file(str(tree_path))
    return WizardSessionService(tree)

@jobs_bp.get("/dashboard")
@login_required
def dashboard():
    counts = {s: Job.query.filter_by(status=s).count() for s in JobStatus.ALL}
    unassigned = Job.query.filter(Job.assigned_primary_user_id.is_(None)).order_by(Job.created_at.desc()).limit(20).all()
    mine = Job.query.filter_by(assigned_primary_user_id=current_user.id).order_by(Job.created_at.desc()).limit(20).all()
    return render_template("jobs/dashboard.html", counts=counts, unassigned=unassigned, mine=mine)


@jobs_bp.post("/<int:job_id>/archive")
@login_required
def archive_job(job_id):
    job = Job.query.get_or_404(job_id)
    if current_user.role not in ("admin", "analyst"):
        abort(403)
    job.status = JobStatus.ARCHIVED
    db.session.add(JobEvent(
        job_id=job.id,
        actor_user_id=current_user.id,
        event_type="ARCHIVED",
        payload_json=None
    ))
    db.session.commit()
    flash("Job archived.", "info")
    return redirect(url_for("jobs.list_jobs"))


@jobs_bp.route("/new-wizard", methods=["GET", "POST"])
@login_required
def new_job_wizard():
    form = NewJobWizardForm()
    form.project_type.choices = [(x, x) for x in ProjectType.ALL]
    form.ms_mode.choices = [(x, x) for x in MSMode.ALL]
    form.tmt_label_type.choices = [(x, x) for x in TMTLabelType.ALL]
    form.search_engines_mode.choices = [(x, x) for x in SearchEnginesMode.ALL]

    if request.method == "GET":
        preset = request.args.get("preset", "")
        if preset:
            form.preset.data = preset
            if preset == "MHC1_STANDARD":
                form.project_type.data = "IMMPep_MHC1"
                form.search_engines_mode.data = "BASIC_COMET"
                form.db_canonical.data = True
                form.val_hla_binding.data = True
            elif preset == "MHC2_STANDARD":
                form.project_type.data = "IMMPep_MHC2"
                form.search_engines_mode.data = "BASIC_COMET"
                form.db_canonical.data = True
                form.val_hla_binding.data = True
            elif preset == "MICRO_ROUNDS":
                form.project_type.data = "MICROPROTEOME"
                form.search_engines_mode.data = "MULTI_SEARCH"
                form.db_basic_noncanonical.data = True
                form.micro_rounds_enabled.data = True
                form.micro_rounds_text.data = "8-13\n14-24\n25-35"
            elif preset == "KITCHEN_SINK":
                form.project_type.data = "OTHER"
                form.search_engines_mode.data = "FULL_SEARCH"
                form.db_full_nonc.data = True
                form.val_rnaseq_quant.data = True
                form.db_requirements_text.data = "Requires RNAseq (RIN > 6 recommended)."

    if request.method == "POST" and form.validate_on_submit():
        if form.tmt_label_type.data != TMTLabelType.LF and not form.tmt_plex.data:
            flash("TMT plex is required when using TMT labelling.", "warning")
            return render_template("jobs/new_wizard.html", form=form)

        project = Project.query.filter_by(name=form.project_name.data.strip()).first()
        if not project:
            project = Project(
                name=form.project_name.data.strip(),
                owner_user_id=current_user.id,
                partners_text=form.project_partners.data.strip() if form.project_partners.data else None,
                short_description=form.sample_description.data.strip() if form.sample_description.data else None,
                created_by_user_id=current_user.id,
            )
            db.session.add(project)
            db.session.flush()

        job = Job(
            project_id=project.id,
            submitted_by_user_id=current_user.id,
            status=JobStatus.SUBMITTED,
            priority=form.priority.data
        )
        db.session.add(job)
        db.session.flush()

        sc = SearchConfig(
            job_id=job.id,
            project_type=form.project_type.data,
            species=form.species.data.strip(),
            instrument=form.instrument.data.strip() if form.instrument.data else None,
            ms_mode=form.ms_mode.data,
            tmt_label_type=form.tmt_label_type.data,
            tmt_plex=form.tmt_plex.data,
            tmt_labelling_schema=form.tmt_labelling_schema.data.strip() if form.tmt_labelling_schema.data else None,
            carbamidomethylated=bool(form.carbamidomethylated.data),
            additional_mods=[m.strip() for m in (form.additional_mods.data or "").split(",") if m.strip()],
            sample_description=form.sample_description.data.strip() if form.sample_description.data else None,
            search_engines_mode=form.search_engines_mode.data,
            additional_searches=[x.strip() for x in (form.additional_searches.data or "").split(",") if x.strip()],
            hla_typing_information=form.hla_typing_information.data.strip() if form.hla_typing_information.data else None,
        )
        db.session.add(sc)

        vc = ValidationConfig(
            job_id=job.id,
            hla_binding=bool(form.val_hla_binding.data),
            conflict_resolution_delta_score_filter=bool(form.val_conflict_delta.data),
            pep_filter=bool(form.val_pep_filter.data),
            two_search_engine_agreement=bool(form.val_two_engine.data),
            pd_infrys_validation=bool(form.val_pd_infrys.data),
            pepquery=bool(form.val_pepquery.data),
            rnaseq_mapping_read_quant=bool(form.val_rnaseq_quant.data),
            genome_mapping_tool=(form.val_genome_mapping.data or "").strip() or None,
            immunogenicity_analysis=bool(form.val_immunogenicity.data),
        )
        db.session.add(vc)

        raw_lines = [ln.strip() for ln in (form.raw_files_multiline.data or "").splitlines() if ln.strip()]
        for ln in raw_lines:
            db.session.add(JobRawFile(job_id=job.id, location_uri=ln))

        req_text = form.db_requirements_text.data.strip() if form.db_requirements_text.data else None

        def add_db(tier: str, rank: int, fasta: str | None = None, requires_rnaseq: bool = False):
            db.session.add(DatabaseRequest(
                job_id=job.id,
                db_tier=tier,
                rank_level=rank,
                requires_rnaseq=requires_rnaseq,
                requirements_text=req_text,
                fasta_location=fasta,
            ))

        if form.db_canonical.data:
            add_db(DatabaseTier.CANONICAL_ONLY, 1)
        if form.db_basic_noncanonical.data:
            add_db(DatabaseTier.BASIC_NON_CANONICAL, 2)
        if form.db_cancer_specific.data:
            add_db(DatabaseTier.CANCER_BIOTYPE_SPECIFIC, 3)
        if form.db_full_nonc.data:
            add_db(DatabaseTier.FULL_NON_CANONICAL, 4, requires_rnaseq=True)
        if form.db_personal.data:
            if not form.personal_fasta_location.data:
                flash("Personal DB selected: FASTA location is required.", "warning")
                return render_template("jobs/new_wizard.html", form=form)
            add_db(DatabaseTier.PERSONAL_DB, 5, fasta=form.personal_fasta_location.data.strip())
        if form.db_special_fasta.data:
            if not form.special_fasta_location.data:
                flash("Special FASTA selected: FASTA location is required.", "warning")
                return render_template("jobs/new_wizard.html", form=form)
            add_db(DatabaseTier.SPECIAL_FASTA, 6, fasta=form.special_fasta_location.data.strip())

        if vc.pepquery:
            has_rank3 = DatabaseRequest.query.filter(
                DatabaseRequest.job_id == job.id,
                DatabaseRequest.rank_level >= 3
            ).count() > 0
            if not has_rank3:
                vc.pepquery = False
                flash("PepQuery requires a DB request at rank 3+ (auto-disabled).", "warning")

        if form.micro_rounds_enabled.data:
            rounds = [ln.strip() for ln in (form.micro_rounds_text.data or "").splitlines() if ln.strip()]
            for r in rounds:
                if "-" in r:
                    a, b = r.split("-", 1)
                    a, b = int(a.strip()), int(b.strip())
                    db.session.add(MicroproteomeRound(
                        job_id=job.id,
                        round_name=f"{a}-{b}",
                        min_len=a,
                        max_len=b,
                        enabled=True
                    ))

        db.session.add(JobEvent(
            job_id=job.id,
            actor_user_id=current_user.id,
            event_type="JOB_CREATED_WIZARD",
            payload_json={"project_name": project.name}
        ))
        db.session.commit()
        flash("OMS job created.", "success")
        return redirect(url_for("jobs.job_detail", job_id=job.id))

    return render_template("jobs/new_wizard.html", form=form)


@jobs_bp.get("/")
@login_required
def list_jobs():
    status = request.args.get("status")
    q = Job.query.filter(Job.status != JobStatus.ARCHIVED).order_by(Job.created_at.desc())
    if status:
        q = q.filter(Job.status == status)
    jobs = q.limit(100).all()

    return render_template("jobs/list.html", jobs=jobs, status=status, statuses=JobStatus.ALL)


@jobs_bp.get("/new")
@login_required
def new_job():
    form = NewJobForm()
    return render_template("jobs/new.html", form=form)


@jobs_bp.post("/new")
@login_required
def new_job_post():
    form = NewJobForm()
    if not form.validate_on_submit():
        return render_template("jobs/new.html", form=form), 400

    owner_name = form.project_owner.data.strip()
    project = Project(
        name=form.project_name.data.strip(),
        owner_user_id=current_user.id,
        partners_text=form.project_partners.data.strip() if form.project_partners.data else None,
        short_description=form.short_description.data.strip() if form.short_description.data else None,
        created_by_user_id=current_user.id
    )
    db.session.add(project)
    db.session.flush()

    job = Job(
        project_id=project.id,
        submitted_by_user_id=current_user.id,
        priority=form.priority.data,
        status=JobStatus.SUBMITTED
    )
    db.session.add(job)
    db.session.flush()

    db.session.add(SearchConfig(job_id=job.id))
    db.session.add(ValidationConfig(job_id=job.id))

    db.session.add(JobEvent(
        job_id=job.id,
        actor_user_id=current_user.id,
        event_type="CREATED",
        payload_json={
            "project_owner_text": owner_name,
            "priority": job.priority,
            "status": job.status
        }
    ))
    db.session.commit()
    flash(f"Job #{job.id} created.", "success")
    return redirect(url_for("jobs.list_jobs"))


def _get_job_or_404(job_id: int) -> Job:
    job = Job.query.get(job_id)
    if not job:
        abort(404)
    return job


def _require_analyst():
    if not current_user.is_authenticated or not getattr(current_user, "is_analyst", lambda: False)():
        abort(403)


@jobs_bp.post("/<int:job_id>/assign")
@login_required
def assign_job(job_id: int):
    _require_analyst()
    job = _get_job_or_404(job_id)
    form = AssignJobForm()
    analysts = User.query.filter(User.role.in_([Role.ADMIN, Role.ANALYST]), User.is_active == True).order_by(User.name.asc()).all()
    form.assignee_user_id.choices = [(u.id, f"{u.name} ({u.role})") for u in analysts]
    if not form.validate_on_submit():
        flash("Invalid assignment.", "warning")
        return redirect(url_for("jobs.job_detail", job_id=job.id))
    assignee_id = form.assignee_user_id.data
    job.assigned_primary_user_id = assignee_id
    db.session.add(JobAssignment(job_id=job.id, user_id=assignee_id, role="primary"))
    db.session.add(JobEvent(
        job_id=job.id,
        actor_user_id=current_user.id,
        event_type="ASSIGNED",
        payload_json={"assignee_user_id": assignee_id}
    ))
    if job.status == JobStatus.SUBMITTED:
        job.status = JobStatus.TRIAGED
        db.session.add(JobEvent(
            job_id=job.id,
            actor_user_id=current_user.id,
            event_type="STATUS_CHANGED",
            payload_json={"from": JobStatus.SUBMITTED, "to": JobStatus.TRIAGED}
        ))
    db.session.commit()
    flash("Job assigned.", "success")
    return redirect(url_for("jobs.job_detail", job_id=job.id))


@jobs_bp.post("/<int:job_id>/status")
@login_required
def update_status(job_id: int):
    _require_analyst()
    job = _get_job_or_404(job_id)
    form = UpdateStatusForm()
    form.status.choices = [(s, s) for s in JobStatus.ALL]
    if not form.validate_on_submit():
        flash("Invalid status.", "warning")
        return redirect(url_for("jobs.job_detail", job_id=job.id))
    new_status = form.status.data
    old_status = job.status
    if new_status != old_status:
        job.status = new_status
        db.session.add(JobEvent(
            job_id=job.id,
            actor_user_id=current_user.id,
            event_type="STATUS_CHANGED",
            payload_json={"from": old_status, "to": new_status}
        ))
        db.session.commit()
        flash("Status updated.", "success")
    return redirect(url_for("jobs.job_detail", job_id=job.id))


@jobs_bp.get("/<int:job_id>/export.json")
@login_required
def export_job_json(job_id: int):
    job = _get_job_or_404(job_id)
    sc = SearchConfig.query.get(job.id)
    vc = ValidationConfig.query.get(job.id)
    raw_files = JobRawFile.query.filter_by(job_id=job.id).all()
    db_reqs = DatabaseRequest.query.filter_by(job_id=job.id).order_by(DatabaseRequest.rank_level.asc()).all()
    rounds = MicroproteomeRound.query.filter_by(job_id=job.id).order_by(MicroproteomeRound.min_len.asc()).all()
    payload = {
        "job": {
            "id": job.id,
            "status": job.status,
            "priority": job.priority,
            "project": {"id": job.project.id, "name": job.project.name},
            "assigned_primary_user_id": job.assigned_primary_user_id,
            "created_at": job.created_at.isoformat() if job.created_at else None,
        },
        "search_config": None if not sc else {
            "project_type": sc.project_type,
            "species": sc.species,
            "instrument": sc.instrument,
            "ms_mode": sc.ms_mode,
            "tmt_label_type": sc.tmt_label_type,
            "tmt_plex": sc.tmt_plex,
            "tmt_labelling_schema": sc.tmt_labelling_schema,
            "carbamidomethylated": sc.carbamidomethylated,
            "additional_mods": sc.additional_mods or [],
            "sample_description": sc.sample_description,
            "search_engines_mode": sc.search_engines_mode,
            "additional_searches": sc.additional_searches or [],
            "hla_typing_information": sc.hla_typing_information,
        },
        "raw_files": [{"location_uri": r.location_uri, "notes": r.notes} for r in raw_files],
        "database_requests": [
            {
                "db_tier": d.db_tier,
                "rank_level": d.rank_level,
                "requires_rnaseq": d.requires_rnaseq,
                "requirements_text": d.requirements_text,
                "fasta_location": d.fasta_location,
                "notes": d.notes,
            }
            for d in db_reqs
        ],
        "microproteome_rounds": [
            {"round_name": r.round_name, "min_len": r.min_len, "max_len": r.max_len, "enabled": r.enabled}
            for r in rounds
        ],
        "validation_config": None if not vc else {
            "hla_binding": vc.hla_binding,
            "conflict_resolution_delta_score_filter": vc.conflict_resolution_delta_score_filter,
            "pep_filter": vc.pep_filter,
            "two_search_engine_agreement": vc.two_search_engine_agreement,
            "pd_infrys_validation": vc.pd_infrys_validation,
            "pepquery": vc.pepquery,
            "rnaseq_mapping_read_quant": vc.rnaseq_mapping_read_quant,
            "genome_mapping_tool": vc.genome_mapping_tool,
            "immunogenicity_analysis": vc.immunogenicity_analysis,
            "notes": vc.notes,
        },
    }
    db.session.add(JobEvent(
        job_id=job.id,
        actor_user_id=current_user.id,
        event_type="EXPORTED_JSON",
        payload_json={"format": "json"}
    ))
    db.session.commit()
    plan = {
        "search_engines": [],
        "extra_searches": (payload.get("search_config") or {}).get("additional_searches", []),
        "db_ranks": [d["rank_level"] for d in payload.get("database_requests", [])],
        "requires_rnaseq": any(d["requires_rnaseq"] for d in payload.get("database_requests", [])),
        "micro_rounds": payload.get("microproteome_rounds", []),
    }

    scp = payload.get("search_config") or {}
    mode = scp.get("search_engines_mode")

    if mode == "BASIC_COMET":
        plan["search_engines"] = ["COMET"]
    elif mode == "MULTI_COMET_MSFRAGGER":
        plan["search_engines"] = ["COMET", "MSFRAGGER"]
    elif mode == "FULL_ALL":
        plan["search_engines"] = ["COMET", "MSFRAGGER", "OTHER_ENGINES"]

    payload["pipeline_plan"] = plan
    return jsonify(payload)


@jobs_bp.get("/<int:job_id>")
@login_required
def job_detail(job_id: int):
    analysts = User.query.filter(User.role.in_([Role.ADMIN, Role.ANALYST]), User.is_active == True).order_by(User.name.asc()).all()
    job = _get_job_or_404(job_id)
    sc = SearchConfig.query.get(job.id)
    vc = ValidationConfig.query.get(job.id)
    raw_files = JobRawFile.query.filter_by(job_id=job.id).order_by(JobRawFile.created_at.desc()).all()
    db_reqs = DatabaseRequest.query.filter_by(job_id=job.id).order_by(DatabaseRequest.rank_level.asc()).all()
    rounds = MicroproteomeRound.query.filter_by(job_id=job.id).order_by(MicroproteomeRound.min_len.asc()).all()
    return render_template(
        "jobs/detail.html",
        job=job,
        search_config=sc,
        validation_config=vc,
        raw_files=raw_files,
        db_reqs=db_reqs,
        rounds=rounds,
        analysts=analysts,
    )


@jobs_bp.route("/<int:job_id>/config", methods=["GET", "POST"])
@login_required
def edit_config(job_id: int):
    job = _get_job_or_404(job_id)
    sc = SearchConfig.query.get(job.id) or SearchConfig(job_id=job.id)
    vc = ValidationConfig.query.get(job.id) or ValidationConfig(job_id=job.id)
    db.session.add(sc)
    db.session.add(vc)
    db.session.flush()
    sc_form = SearchConfigForm(obj=sc)
    vc_form = ValidationConfigForm(obj=vc)
    sc_form.project_type.choices = [(x, x) for x in ProjectType.ALL]
    sc_form.ms_mode.choices = [(x, x) for x in MSMode.ALL]
    sc_form.tmt_label_type.choices = [(x, x) for x in TMTLabelType.ALL]
    sc_form.search_engines_mode.choices = [(x, x) for x in SearchEnginesMode.ALL]
    if request.method == "GET":
        sc_form.additional_mods.data = ", ".join(sc.additional_mods or [])
        sc_form.additional_searches.data = ", ".join(sc.additional_searches or [])
    if request.method == "POST":
        which = request.form.get("_which")
        if which == "search" and sc_form.validate_on_submit():
            sc.project_type = sc_form.project_type.data
            sc.species = sc_form.species.data.strip()
            sc.instrument = (sc_form.instrument.data or "").strip() or None
            sc.ms_mode = sc_form.ms_mode.data
            sc.tmt_label_type = sc_form.tmt_label_type.data
            sc.tmt_plex = sc_form.tmt_plex.data
            sc.tmt_labelling_schema = (sc_form.tmt_labelling_schema.data or "").strip() or None
            sc.carbamidomethylated = bool(sc_form.carbamidomethylated.data)
            mods = (sc_form.additional_mods.data or "").strip()
            sc.additional_mods = [m.strip() for m in mods.split(",") if m.strip()] if mods else []
            sc.sample_description = (sc_form.sample_description.data or "").strip() or None
            sc.search_engines_mode = sc_form.search_engines_mode.data
            extras = (sc_form.additional_searches.data or "").strip()
            sc.additional_searches = [x.strip() for x in extras.split(",") if x.strip()] if extras else []
            sc.hla_typing_information = (sc_form.hla_typing_information.data or "").strip() or None
            if sc.tmt_label_type != TMTLabelType.LF:
                if not sc.tmt_plex:
                    flash("TMT plex is required when using TMT labelling.", "warning")
                    return redirect(url_for("jobs.edit_config", job_id=job.id))
            db.session.add(JobEvent(
                job_id=job.id,
                actor_user_id=current_user.id,
                event_type="CONFIG_UPDATED",
                payload_json={"section": "search_config"}
            ))
            db.session.commit()
            flash("Search config saved.", "success")
            return redirect(url_for("jobs.edit_config", job_id=job.id))
        if which == "validation" and vc_form.validate_on_submit():
            vc.hla_binding = bool(vc_form.hla_binding.data)
            vc.conflict_resolution_delta_score_filter = bool(vc_form.conflict_resolution_delta_score_filter.data)
            vc.pep_filter = bool(vc_form.pep_filter.data)
            vc.two_search_engine_agreement = bool(vc_form.two_search_engine_agreement.data)
            vc.pd_infrys_validation = bool(vc_form.pd_infrys_validation.data)
            vc.pepquery = bool(vc_form.pepquery.data)
            vc.rnaseq_mapping_read_quant = bool(vc_form.rnaseq_mapping_read_quant.data)
            vc.genome_mapping_tool = (vc_form.genome_mapping_tool.data or "").strip() or None
            vc.immunogenicity_analysis = bool(vc_form.immunogenicity_analysis.data)
            vc.notes = (vc_form.notes.data or "").strip() or None
            if vc.pepquery:
                has_rank3 = DatabaseRequest.query.filter(
                    DatabaseRequest.job_id == job.id,
                    DatabaseRequest.rank_level >= 3
                ).count() > 0
                if not has_rank3:
                    vc.pepquery = False
                    flash("PepQuery requires at least one database request with rank level 3+.", "warning")
            db.session.add(JobEvent(
                job_id=job.id,
                actor_user_id=current_user.id,
                event_type="CONFIG_UPDATED",
                payload_json={"section": "validation_config"}
            ))
            db.session.commit()
            flash("Validation config saved.", "success")
            return redirect(url_for("jobs.edit_config", job_id=job.id))
        flash("Please fix the form errors.", "warning")
    return render_template("jobs/config.html", job=job, sc_form=sc_form, vc_form=vc_form)


@jobs_bp.route("/<int:job_id>/raw-files", methods=["GET", "POST"])
@login_required
def raw_files(job_id: int):
    job = _get_job_or_404(job_id)
    form = RawFileForm()
    if form.validate_on_submit():
        rf = JobRawFile(
            job_id=job.id,
            location_uri=form.location_uri.data.strip(),
            notes=(form.notes.data or "").strip() or None
        )
        db.session.add(rf)
        db.session.add(JobEvent(
            job_id=job.id,
            actor_user_id=current_user.id,
            event_type="RAW_FILE_ADDED",
            payload_json={"location_uri": rf.location_uri}
        ))
        db.session.commit()
        flash("Raw file added.", "success")
        return redirect(url_for("jobs.raw_files", job_id=job.id))
    items = JobRawFile.query.filter_by(job_id=job.id).order_by(JobRawFile.created_at.desc()).all()
    return render_template("jobs/raw_files.html", job=job, form=form, items=items)


@jobs_bp.route("/<int:job_id>/databases", methods=["GET", "POST"])
@login_required
def databases(job_id: int):
    job = _get_job_or_404(job_id)
    form = DatabaseRequestForm()
    form.db_tier.choices = [(x, x) for x in DatabaseTier.ALL]
    if form.validate_on_submit():
        dr = DatabaseRequest(
            job_id=job.id,
            db_tier=form.db_tier.data,
            rank_level=form.rank_level.data,
            requires_rnaseq=bool(form.requires_rnaseq.data),
            requirements_text=(form.requirements_text.data or "").strip() or None,
            fasta_location=(form.fasta_location.data or "").strip() or None,
            notes=(form.notes.data or "").strip() or None,
        )
        if dr.db_tier == DatabaseTier.FULL_NON_CANONICAL:
            dr.requires_rnaseq = True
            if not dr.requirements_text:
                dr.requirements_text = "Requires RNAseq (RIN > 6 recommended)."
        if dr.db_tier in (DatabaseTier.PERSONAL_DB, DatabaseTier.SPECIAL_FASTA) and not dr.fasta_location:
            flash("FASTA location is required for Personal DB / Special FASTA requests.", "warning")
            return redirect(url_for("jobs.databases", job_id=job.id))
        db.session.add(dr)
        db.session.add(JobEvent(
            job_id=job.id,
            actor_user_id=current_user.id,
            event_type="DB_REQUEST_ADDED",
            payload_json={"db_tier": dr.db_tier, "rank_level": dr.rank_level}
        ))
        db.session.commit()
        flash("Database request added.", "success")
        return redirect(url_for("jobs.databases", job_id=job.id))
    items = DatabaseRequest.query.filter_by(job_id=job.id).order_by(DatabaseRequest.rank_level.asc()).all()
    return render_template("jobs/databases.html", job=job, form=form, items=items)


@jobs_bp.route("/<int:job_id>/micro-rounds", methods=["GET", "POST"])
@login_required
def micro_rounds(job_id: int):
    job = _get_job_or_404(job_id)
    form = MicroproteomeRoundForm()
    if form.validate_on_submit():
        r = MicroproteomeRound(
            job_id=job.id,
            round_name=form.round_name.data.strip(),
            min_len=form.min_len.data,
            max_len=form.max_len.data,
            enabled=bool(form.enabled.data),
            notes=(form.notes.data or "").strip() or None,
        )
        db.session.add(r)
        db.session.add(JobEvent(
            job_id=job.id,
            actor_user_id=current_user.id,
            event_type="MICRO_ROUND_ADDED",
            payload_json={"round_name": r.round_name, "min_len": r.min_len, "max_len": r.max_len}
        ))
        db.session.commit()
        flash("Microproteome round added.", "success")
        return redirect(url_for("jobs.micro_rounds", job_id=job.id))
    items = MicroproteomeRound.query.filter_by(job_id=job.id).order_by(MicroproteomeRound.min_len.asc()).all()
    return render_template("jobs/micro_rounds.html", job=job, form=form, items=items)


@jobs_bp.post("/<int:job_id>/export/nextflow")
@login_required
def export_nextflow(job_id: int):
    form = CSRFOnlyForm()
    if not form.validate_on_submit():
        abort(400)
    job = db.session.get(Job, job_id)
    if not job:
        abort(404)
    job_dict = job.to_dict() if hasattr(job, "to_dict") else {
        "name": getattr(job, "title", f"job_{job.id}"),
        "steps": getattr(job, "steps", []),
    }
    nf_text = build_nextflow_nf(job_dict)
    buf = io.BytesIO(nf_text.encode("utf-8"))
    filename = f"{safe_slug(job_dict.get('name', f'job_{job.id}'))}.nf"
    return send_file(
        buf,
        mimetype="text/plain",
        as_attachment=True,
        download_name=filename
    )

@jobs_bp.route("/api/wizard/sessions", methods=["POST"])
def wizard_create_session():
    svc = _wizard_service()
    ws = svc.create()
    return jsonify(svc.state(ws)), 201


@jobs_bp.route("/api/wizard/sessions/<int:session_id>/choose", methods=["POST"])
def wizard_choose(session_id: int):
    svc = _wizard_service()
    ws = svc.get(session_id)

    data = request.get_json(silent=True) or {}
    choice = data.get("choice")
    if not choice:
        return jsonify({"error": "Missing 'choice'"}), 400

    try:
        ws = svc.set_choice(ws, choice)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    return jsonify(svc.state(ws))


@jobs_bp.route("/api/wizard/sessions/<int:session_id>/back", methods=["POST"])
def wizard_back(session_id: int):
    svc = _wizard_service()
    ws = svc.get(session_id)
    ws = svc.back(ws)
    return jsonify(svc.state(ws))


@jobs_bp.route("/api/wizard/sessions/<int:session_id>/inputs", methods=["PATCH"])
def wizard_patch_inputs(session_id: int):
    svc = _wizard_service()
    ws = svc.get(session_id)

    data = request.get_json(silent=True) or {}
    ws = svc.set_inputs(ws, data)
    return jsonify(svc.state(ws))


def safe_slug(s: str) -> str:
    s = (s or "").strip().lower()
    out = []
    for ch in s:
        if ch.isalnum() or ch in ("-", "_"):
            out.append(ch)
        elif ch.isspace():
            out.append("_")
    return "".join(out) or "pipeline"


def build_nextflow_nf(job_dict: dict) -> str:
    name = job_dict.get("name", "pipeline")
    steps = job_dict.get("steps", [])
    process_blocks = []
    workflow_calls = []
    for i, step in enumerate(steps, start=1):
        step_name = step.get("name") or f"step_{i}"
        proc_name = safe_slug(step_name).upper()
        cmd = step.get("cmd") or "echo 'TODO: implement step command'"
        process_blocks.append(f"""
process {proc_name} {{
  tag "{step_name}"

  input:
    path input_files

  output:
    path "out_{i}", emit: out

  script:
  \"\"\"
  mkdir -p out_{i}
  {cmd} > out_{i}/log.txt
  \"\"\"
}}
""")
        workflow_calls.append(f"{proc_name}(input_files)")
    if not steps:
        process_blocks.append('''process HELLO {
  output:
    path "results"

  script:
  """
  mkdir -p results
  echo "Hello from Nextflow" > results/hello.txt
  """
}
''')
        workflow_calls.append("HELLO()")
    return f"""\
/*
  Auto-generated by OMS Job App
  Pipeline name: {name}
*/

nextflow.enable.dsl = 2

params.input = params.input ?: "data/*"
params.outdir = params.outdir ?: "results"

workflow {{

  input_files = Channel.fromPath(params.input)

{indent_lines("\\n".join(workflow_calls), 2)}

}}

{chr(10).join(process_blocks)}
"""
import json
from pathlib import Path
from flask import jsonify, current_app
from flask_login import login_required, current_user

from app.models.wizard_session import WizardSession
from app.models.job import Job, JobStatus, JobPriority, JobEvent
from app.models import Project
from app.extensions import db


def _wizard_missing_required(profile: str, inputs: dict) -> list[str]:
    missing = []
    for k in ["mzml_input_dir", "database", "out_dir"]:
        if not inputs.get(k):
            missing.append(k)

    if profile.startswith("HLA_"):
        if not inputs.get("hla_prediction", False) and not inputs.get("HLA"):
            missing.append("HLA")

    if inputs.get("tmt") is True and not inputs.get("isotype"):
        missing.append("isotype")

    return missing


@jobs_bp.post("/api/wizard/sessions/<int:session_id>/submit")
@login_required
def wizard_submit(session_id: int):
    ws = WizardSession.query.get_or_404(session_id)

    if not ws.profile:
        return jsonify({"error": "Wizard session not complete (no profile resolved)."}), 400

    inputs = ws.inputs or {}
    missing = _wizard_missing_required(ws.profile, inputs)
    if missing:
        return jsonify({"error": "Missing required inputs", "missing": missing}), 400

    # If you haven't added project fields to the wizard yet, we generate a minimal project.
    project_name = inputs.get("project_name") or f"Wizard Project (session {ws.id})"

    project = Project(
        name=project_name,
        owner_user_id=current_user.id,
        created_by_user_id=current_user.id,
        partners_text=inputs.get("project_partners"),
        short_description=inputs.get("short_description"),
    )
    db.session.add(project)
    db.session.flush()

    priority = (inputs.get("priority") or JobPriority.NORMAL).upper()
    if priority not in JobPriority.ALL:
        priority = JobPriority.NORMAL

    job = Job(
        project_id=project.id,
        submitted_by_user_id=current_user.id,
        priority=priority,
        status=JobStatus.SUBMITTED,

        job_kind="PRESET",
        nf_profile=ws.profile,
        nf_params=inputs,
    )
    db.session.add(job)
    db.session.flush()

    # same defaults as /jobs/new
    db.session.add(SearchConfig(job_id=job.id))
    db.session.add(ValidationConfig(job_id=job.id))

    # Write run artifacts
    run_dir = Path(current_app.instance_path) / "jobs" / str(job.id)
    run_dir.mkdir(parents=True, exist_ok=True)

    params_path = run_dir / "params.json"
    params_path.write_text(json.dumps(inputs, indent=2), encoding="utf-8")

    repo_root = Path(current_app.root_path).parent
    pipeline_path = repo_root / "pipeline" / "main.nf"
    config_path = repo_root / "pipeline" / "nextflow.config"

    run_sh = run_dir / "run.sh"
    run_sh.write_text(
        "\n".join([
            "#!/usr/bin/env bash",
            "set -euo pipefail",
            f'nextflow run "{pipeline_path}" -c "{config_path}" -profile "{ws.profile}" -params-file "{params_path}"',
            ""
        ]),
        encoding="utf-8"
    )
    run_sh.chmod(0o755)

    (run_dir / "profile.txt").write_text(ws.profile + "\n", encoding="utf-8")

    (run_dir / "nextflow.config.snapshot").write_text(
        Path(config_path).read_text(encoding="utf-8"),
        encoding="utf-8"
    )

    job.run_dir = str(run_dir)

    db.session.add(JobEvent(
        job_id=job.id,
        actor_user_id=current_user.id,
        event_type="CREATED_FROM_WIZARD",
        payload_json={
            "wizard_session_id": ws.id,
            "path": [p for p in (session.path or []) if p != "options"]
            "profile": ws.profile,
        }
    ))

    ws.status = "submitted"
    db.session.commit()

    return jsonify({
        "job_id": job.id,
        "project_id": project.id,
        "wizard_session_id": ws.id,
        "profile": ws.profile,
        "run_dir": job.run_dir,
        "detail_url": url_for("jobs.job_detail", job_id=job.id),
    }), 201


from flask import render_template_string
from flask_login import login_required

@jobs_bp.get("/wizard-test-submit/<int:session_id>")
@login_required
def wizard_test_submit_page(session_id: int):
    return render_template_string("""
    <h1>Wizard submit test</h1>
    <form method="post" action="/jobs/api/wizard/sessions/{{sid}}/submit">
      <button type="submit">Submit wizard session {{sid}}</button>
    </form>
    """, sid=session_id)

def indent_lines(text: str, spaces: int) -> str:
    pad = " " * spaces
    return "\n".join(pad + line if line.strip() else line for line in text.splitlines())