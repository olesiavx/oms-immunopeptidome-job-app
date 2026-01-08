from flask_wtf import FlaskForm
from wtforms import (
    StringField, TextAreaField, SelectField, SubmitField, BooleanField, IntegerField
)
from wtforms.validators import DataRequired, Length, Optional, NumberRange


class NewJobForm(FlaskForm):
    project_name = StringField("Project Name", validators=[DataRequired(), Length(max=255)])
    project_owner = StringField("Project Owner (who is this for)", validators=[DataRequired(), Length(max=255)])
    project_partners = StringField("Project Partner(s)", validators=[Length(max=255)])
    short_description = TextAreaField("Short Sample / Experiment Description")

    priority = SelectField(
        "Priority",
        choices=[("LOW","LOW"),("NORMAL","NORMAL"),("HIGH","HIGH"),("URGENT","URGENT")],
        default="NORMAL",
        validators=[DataRequired()]
    )

    submit = SubmitField("Create Job")

class SearchConfigForm(FlaskForm):
    project_type = SelectField("Project type", validators=[DataRequired()])
    species = StringField("Species", validators=[DataRequired(), Length(max=128)])
    instrument = StringField("Instrument", validators=[Optional(), Length(max=128)])

    ms_mode = SelectField("MS mode", validators=[DataRequired()])

    tmt_label_type = SelectField("TMT labelling type", validators=[DataRequired()])
    tmt_plex = IntegerField("TMT plex (6,10,11,16,18,32)", validators=[Optional()])
    tmt_labelling_schema = TextAreaField("TMT labelling schema", validators=[Optional()])

    carbamidomethylated = BooleanField("Carbamidomethylated", default=True)
    additional_mods = StringField(
        "Additional mods (comma-separated)",
        validators=[Optional(), Length(max=512)]
    )

    sample_description = TextAreaField("Short sample/experiment description", validators=[Optional()])

    search_engines_mode = SelectField("Search engines mode", validators=[DataRequired()])
    additional_searches = StringField(
        "Additional searches (comma-separated: PEAKs, FragPipe, PD_Infrys)",
        validators=[Optional(), Length(max=512)]
    )

    hla_typing_information = TextAreaField("HLA typing information", validators=[Optional()])

    submit = SubmitField("Save config")


class ValidationConfigForm(FlaskForm):
    hla_binding = BooleanField("HLA binding")
    conflict_resolution_delta_score_filter = BooleanField("Conflict resolution (Delta score filter)")
    pep_filter = BooleanField("PEP filter")
    two_search_engine_agreement = BooleanField("2 search engine agreement")
    pd_infrys_validation = BooleanField("PD Infrys")

    pepquery = BooleanField("PepQuery (only for DB search rank 3+ later rule)")

    rnaseq_mapping_read_quant = BooleanField("RNAseq mapping / read quant")
    genome_mapping_tool = SelectField(
        "Genome mapping tool",
        choices=[("", "(none)"), ("PeptiMapper", "PeptiMapper"), ("BamQuery", "BamQuery")],
        validators=[Optional()],
        default=""
    )
    immunogenicity_analysis = BooleanField("Immunogenicity analysis")

    notes = TextAreaField("Notes", validators=[Optional()])

    submit = SubmitField("Save validation")


class RawFileForm(FlaskForm):
    location_uri = StringField("Raw file location (path/URI)", validators=[DataRequired(), Length(max=2048)])
    notes = StringField("Notes", validators=[Optional(), Length(max=255)])
    submit = SubmitField("Add raw file")


class DatabaseRequestForm(FlaskForm):
    db_tier = SelectField("Database tier", validators=[DataRequired()])
    rank_level = IntegerField("Ranking level (1-6)", validators=[DataRequired(), NumberRange(min=1, max=6)])

    requires_rnaseq = BooleanField("Requires RNAseq")
    requirements_text = TextAreaField("Requirements (RIN>6, depth, etc.)", validators=[Optional()])

    fasta_location = StringField("FASTA location (if needed)", validators=[Optional(), Length(max=2048)])
    notes = TextAreaField("Notes", validators=[Optional()])

    submit = SubmitField("Add database request")


class MicroproteomeRoundForm(FlaskForm):
    round_name = StringField("Round name (e.g. 8-13)", validators=[DataRequired(), Length(max=32)])
    min_len = IntegerField("Min length", validators=[DataRequired(), NumberRange(min=1, max=200)])
    max_len = IntegerField("Max length", validators=[DataRequired(), NumberRange(min=1, max=200)])
    enabled = BooleanField("Enabled", default=True)
    notes = TextAreaField("Notes", validators=[Optional()])
    submit = SubmitField("Add round")

class AssignJobForm(FlaskForm):
    assignee_user_id = SelectField("Assign to", coerce=int, validators=[DataRequired()])
    submit = SubmitField("Assign")

class UpdateStatusForm(FlaskForm):
    status = SelectField("Status", validators=[DataRequired()])
    submit = SubmitField("Update status")