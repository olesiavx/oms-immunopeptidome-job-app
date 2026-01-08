from flask_wtf import FlaskForm
from wtforms import (
    StringField, TextAreaField, SelectField, SubmitField, BooleanField, IntegerField
)
from wtforms.validators import DataRequired, Optional, Length, NumberRange


class NewJobWizardForm(FlaskForm):
    preset = SelectField(
    "Preset",
    choices=[
        ("", "(none)"),
        ("MHC1_STANDARD", "Immpep MHC-I Standard (COMET + Canonical)"),
        ("MHC2_STANDARD", "Immpep MHC-II Standard (COMET + Canonical)"),
        ("MICRO_ROUNDS", "Microproteome multi-round (8-13, 14-24, 25-35)"),
        ("KITCHEN_SINK", "Full Non-Canonical (Kitchen Sink) + RNAseq"),
    ],
    default="",
)
    project_name = StringField("Project Name", validators=[DataRequired(), Length(max=255)])
    project_owner = StringField("Project Owner (who is this for)", validators=[DataRequired(), Length(max=255)])
    project_partners = StringField("Project Partner(s)", validators=[Optional(), Length(max=255)])

    project_type = SelectField("Project type", validators=[DataRequired()])
    species = StringField("Species", validators=[DataRequired(), Length(max=128)])
    instrument = StringField("Instrument", validators=[Optional(), Length(max=128)])
    ms_mode = SelectField("MS mode", validators=[DataRequired()])

    tmt_label_type = SelectField("TMT labelling type", validators=[DataRequired()])
    tmt_plex = IntegerField("TMT plex", validators=[Optional(), NumberRange(min=1, max=64)])
    tmt_labelling_schema = TextAreaField("TMT labelling schema", validators=[Optional()])

    carbamidomethylated = BooleanField("Carbamidomethylated", default=True)
    additional_mods = StringField("Additional mods (comma-separated)", validators=[Optional(), Length(max=512)])

    sample_description = TextAreaField("Short sample/experiment description", validators=[Optional()])
    hla_typing_information = TextAreaField("HLA typing information", validators=[Optional()])

    search_engines_mode = SelectField("Search engines mode", validators=[DataRequired()])
    additional_searches = StringField("Additional searches (comma-separated)", validators=[Optional(), Length(max=512)])

    raw_files_multiline = TextAreaField("Raw file locations (one per line)", validators=[Optional()])

    db_canonical = BooleanField("Canonical Only (Rank 1)")
    db_basic_noncanonical = BooleanField("Basic Non-Canonical (Rank 2)")
    db_cancer_specific = BooleanField("Cancer / Biotype Specific (Rank 3)")
    db_full_nonc = BooleanField("Full Non-Canonical (Kitchen Sink) (Rank 4)")
    db_personal = BooleanField("Personal DB (Rank 5)")
    db_special_fasta = BooleanField("Additional special FASTA (Rank 6)")

    personal_fasta_location = StringField("Personal DB FASTA location", validators=[Optional(), Length(max=2048)])
    special_fasta_location = StringField("Special FASTA location", validators=[Optional(), Length(max=2048)])
    db_requirements_text = TextAreaField("DB requirements (RNAseq, RIN, depth, etc.)", validators=[Optional()])

    val_hla_binding = BooleanField("HLA binding")
    val_conflict_delta = BooleanField("Conflict resolution (Delta score filter)")
    val_pep_filter = BooleanField("PEP filter")
    val_two_engine = BooleanField("2 search engine agreement")
    val_pd_infrys = BooleanField("PD Infrys validation")
    val_pepquery = BooleanField("PepQuery (requires rank 3+)")
    val_rnaseq_quant = BooleanField("RNAseq mapping / read quant")
    val_genome_mapping = SelectField(
        "Genome mapping tool",
        choices=[("", "(none)"), ("PeptiMapper", "PeptiMapper"), ("BamQuery", "BamQuery")],
        validators=[Optional()],
        default=""
    )
    val_immunogenicity = BooleanField("Immunogenicity analysis")

    micro_rounds_enabled = BooleanField("Enable microproteome multi-round searches?")
    micro_rounds_text = TextAreaField(
        "Micro rounds (one per line like: 8-13, 14-24, 25-35)",
        validators=[Optional()]
    )

    priority = SelectField(
        "Priority",
        choices=[("LOW","LOW"),("NORMAL","NORMAL"),("HIGH","HIGH"),("URGENT","URGENT")],
        default="NORMAL",
        validators=[DataRequired()]
    )

    submit = SubmitField("Create OMS job")