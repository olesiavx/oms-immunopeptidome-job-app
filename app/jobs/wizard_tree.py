import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

PROFILE_KEY = "__profile__"
DEFAULT_KEY = "_DEFAULT"

class WizardTree:
    def __init__(self, tree: Dict[str, Any]):
        self.tree = tree

    @classmethod
    def from_json_file(cls, path: str) -> "WizardTree":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(data)

    def _node_at_path(self, path: List[str]) -> Any:
        node: Any = self.tree
        for key in path:
            if not isinstance(node, dict) or key not in node:
                raise KeyError(f"Invalid path step '{key}' for path={path}")
            node = node[key]
        return node

    def options(self, path: List[str]) -> List[str]:
        node = self._node_at_path(path)
        if isinstance(node, dict) and PROFILE_KEY in node:
            return []
        if not isinstance(node, dict):
            return []
        keys = [k for k in node.keys() if k not in (PROFILE_KEY, DEFAULT_KEY)]
        return sorted(keys)

    def resolve_profile(self, path: List[str]) -> Tuple[Optional[str], List[str]]:
        node = self._node_at_path(path)

        if isinstance(node, dict) and PROFILE_KEY in node:
            return node[PROFILE_KEY], path

        while isinstance(node, dict) and DEFAULT_KEY in node:
            path = path + [DEFAULT_KEY]
            node = node[DEFAULT_KEY]
            if isinstance(node, dict) and PROFILE_KEY in node:
                return node[PROFILE_KEY], path

        return None, path
    
# app/jobs/wizard_tree.py

# The wizard chooses a path through this tree.
# Leaf nodes resolve to a Nextflow profile name (already defined in pipeline/nextflow.config).
#
# Philosophy:
# - nextflow.config holds the preset defaults
# - wizard collects only user-specific inputs (mzML, FASTA, out_dir, optional HLA)
#
# You can add "required_inputs" and "optional_inputs" per leaf.

WIZARD_TREE = {
    "id": "root",
    "label": "Choose analysis type",
    "options": {
        "HLA": {
            "label": "HLA (immunopeptidomics)",
            "options": {
                "LF": {
                    "label": "Label-free",
                    "profile": "HLA_LF",
                    "required_inputs": ["mzml_input_dir", "database", "out_dir"],
                    "optional_inputs": ["HLA"],
                },
                "TMTpro": {
                    "label": "TMTpro (MHC I)",
                    "profile": "HLA_TMTpro",
                    "required_inputs": ["mzml_input_dir", "database", "out_dir"],
                    "optional_inputs": ["HLA"],
                },
                "TMTpro_MHCII": {
                    "label": "TMTpro (MHC II)",
                    "profile": "HLA_TMTpro_MHCII",
                    "required_inputs": ["mzml_input_dir", "database", "out_dir"],
                    "optional_inputs": ["HLA"],
                },
                "TMT10": {
                    "label": "TMT10 (MHC I)",
                    "profile": "HLA_TMT10",
                    "required_inputs": ["mzml_input_dir", "database", "out_dir"],
                    "optional_inputs": ["HLA"],
                },
                "TMT10_MHCII": {
                    "label": "TMT10 (MHC II)",
                    "profile": "HLA_TMT10_MHCII",
                    "required_inputs": ["mzml_input_dir", "database", "out_dir"],
                    "optional_inputs": ["HLA"],
                },
                "TMT11": {
                    "label": "TMT11 (MHC I)",
                    "profile": "HLA_TMT11",
                    "required_inputs": ["mzml_input_dir", "database", "out_dir"],
                    "optional_inputs": ["HLA"],
                },
            },
        },
        "PRO": {
            "label": "Proteome",
            "options": {
                "TMTpro": {
                    "label": "TMTpro",
                    "options": {
                        "MS3": {
                            "label": "MS3",
                            "profile": "PRO_TMTproMS3",
                            "required_inputs": ["mzml_input_dir", "database", "out_dir"],
                        }
                    },
                },
                "TMT10": {
                    "label": "TMT10",
                    "options": {
                        "MS2": {
                            "label": "MS2",
                            "profile": "PRO_TMT10MS2",
                            "required_inputs": ["mzml_input_dir", "database", "out_dir"],
                            "options": {
                                "SEMI": {
                                    "label": "Semi-enzymatic",
                                    "profile": "PRO_TMT10MS2_SEMI",
                                    "required_inputs": ["mzml_input_dir", "database", "out_dir"],
                                }
                            },
                        }
                    }
                }
            }
        },
    },
}


def get_node_for_path(path: list[str]) -> dict:
    """
    Walk down WIZARD_TREE following tokens in `path`.
    Example path: ["HLA", "TMT10_MHCII"]
    Returns the node dict at that location (or raises KeyError).
    """
    node = WIZARD_TREE
    for token in path:
        opts = node.get("options") or {}
        node = opts[token]
    return node


def get_public_state(path: list[str], inputs: dict) -> dict:
    """
    Returns what the frontend needs to render the current step.
    """
    node = get_node_for_path(path)
    # children are stored under the "options" dict; take its keys as selectable choices
    options = list((node.get("options") or {}).keys())
    # defensive: filter out accidental meta-keys if the tree was authored inconsistently
    options = [k for k in options if k not in ("id", "label", "options")]
    profile = node.get("profile")
    required = node.get("required_inputs") or []
    optional = node.get("optional_inputs") or []
    missing = [k for k in required if not inputs.get(k)]
    complete = bool(profile) and not missing
    return {
        # return the actual path passed in (don't try to read a session variable here)
        "path": list(path),
        "label": node.get("label", ""),
        "options": options,
        "is_leaf": bool(profile),
        "profile": profile,
        "required_inputs": required,
        "optional_inputs": optional,
        "missing": missing,
        "complete": complete,
    }