from datetime import datetime
from ..extensions import db

class ProjectType:
    IMMPEP_MHC1 = "IMMPEP_MHC1"
    IMMPEP_MHC2 = "IMMPEP_MHC2"
    MICROPROTEOME = "MICROPROTEOME"
    WHOLE_PROTEOME = "WHOLE_PROTEOME"
    SEMI_TRYPTIC = "SEMI_TRYPTIC"
    OTHER = "OTHER"

    ALL = [IMMPEP_MHC1, IMMPEP_MHC2, MICROPROTEOME, WHOLE_PROTEOME, SEMI_TRYPTIC, OTHER]

class MSMode:
    MS2 = "MS2"
    MS3 = "MS3"
    DIA = "DIA"
    ALL = [MS2, MS3, DIA]

class TMTLabelType:
    LF = "LF"
    TMTpro = "TMTpro"
    TMT6plex = "TMT6plex"
    ALL = [LF, TMTpro, TMT6plex]

class SearchEnginesMode:
    BASIC_COMET = "BASIC_COMET"
    MULTI_COMET_MSFRAGGER = "MULTI_COMET_MSFRAGGER"
    FULL_ALL = "FULL_ALL"
    ALL = [BASIC_COMET, MULTI_COMET_MSFRAGGER, FULL_ALL]

class DatabaseTier:
    CANONICAL_ONLY = "CANONICAL_ONLY"
    BASIC_NON_CANONICAL = "BASIC_NON_CANONICAL"
    CANCER_BIOTYPE_SPECIFIC = "CANCER_BIOTYPE_SPECIFIC"
    FULL_NON_CANONICAL = "FULL_NON_CANONICAL"
    PERSONAL_DB = "PERSONAL_DB"
    SPECIAL_FASTA = "SPECIAL_FASTA"

    ALL = [CANONICAL_ONLY, BASIC_NON_CANONICAL, CANCER_BIOTYPE_SPECIFIC, FULL_NON_CANONICAL, PERSONAL_DB, SPECIAL_FASTA]


class JobRawFile(db.Model):
    __tablename__ = "job_raw_files"

    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey("jobs.id"), nullable=False, index=True)

    location_uri = db.Column(db.Text, nullable=False)
    notes = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class SearchConfig(db.Model):
    __tablename__ = "search_configs"

    job_id = db.Column(db.Integer, db.ForeignKey("jobs.id"), primary_key=True)

    project_type = db.Column(db.String(64), nullable=False, default=ProjectType.IMMPEP_MHC1)

    species = db.Column(db.String(128), nullable=False, default="Human")
    instrument = db.Column(db.String(128), nullable=True)

    ms_mode = db.Column(db.String(16), nullable=False, default=MSMode.MS2)

    tmt_label_type = db.Column(db.String(32), nullable=False, default=TMTLabelType.LF)
    tmt_plex = db.Column(db.Integer, nullable=True)  
    tmt_labelling_schema = db.Column(db.Text, nullable=True)

    carbamidomethylated = db.Column(db.Boolean, nullable=False, default=True)
    additional_mods = db.Column(db.JSON, nullable=True)  

    sample_description = db.Column(db.Text, nullable=True)

    search_engines_mode = db.Column(db.String(64), nullable=False, default=SearchEnginesMode.BASIC_COMET)
    additional_searches = db.Column(db.JSON, nullable=True)  

    hla_typing_information = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class DatabaseRequest(db.Model):
    __tablename__ = "database_requests"

    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey("jobs.id"), nullable=False, index=True)

    db_tier = db.Column(db.String(64), nullable=False)
    rank_level = db.Column(db.Integer, nullable=False, default=1)  

    requires_rnaseq = db.Column(db.Boolean, nullable=False, default=False)
    requirements_text = db.Column(db.Text, nullable=True)

    fasta_location = db.Column(db.Text, nullable=True)  
    notes = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class MicroproteomeRound(db.Model):
    __tablename__ = "microproteome_rounds"

    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey("jobs.id"), nullable=False, index=True)

    round_name = db.Column(db.String(32), nullable=False) 
    min_len = db.Column(db.Integer, nullable=False)
    max_len = db.Column(db.Integer, nullable=False)

    enabled = db.Column(db.Boolean, nullable=False, default=True)
    notes = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class ValidationConfig(db.Model):
    __tablename__ = "validation_configs"

    job_id = db.Column(db.Integer, db.ForeignKey("jobs.id"), primary_key=True)

    hla_binding = db.Column(db.Boolean, nullable=False, default=False)
    conflict_resolution_delta_score_filter = db.Column(db.Boolean, nullable=False, default=False)
    pep_filter = db.Column(db.Boolean, nullable=False, default=False)
    two_search_engine_agreement = db.Column(db.Boolean, nullable=False, default=False)
    pd_infrys_validation = db.Column(db.Boolean, nullable=False, default=False)

    pepquery = db.Column(db.Boolean, nullable=False, default=False)

    rnaseq_mapping_read_quant = db.Column(db.Boolean, nullable=False, default=False)
    genome_mapping_tool = db.Column(db.String(64), nullable=True)  
    immunogenicity_analysis = db.Column(db.Boolean, nullable=False, default=False)

    notes = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)