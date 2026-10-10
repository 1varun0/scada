import yaml
import os
from types import SimpleNamespace

def load_config(config_path: str = None) -> SimpleNamespace:
    """Load config.yaml and return as a nested SimpleNamespace."""
    if config_path is None:
        # Default to scada_live/config.yaml
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        config_path = os.path.join(base_dir, 'config.yaml')
        
    with open(config_path, 'r') as f:
        config_dict = yaml.safe_load(f)
        
    return _dict_to_namespace(config_dict)

def _dict_to_namespace(d: dict) -> SimpleNamespace:
    """Recursively convert a dict to SimpleNamespace for dot-access."""
    if isinstance(d, dict):
        for k, v in d.items():
            d[k] = _dict_to_namespace(v)
        return SimpleNamespace(**d)
    elif isinstance(d, list):
        return [_dict_to_namespace(i) for i in d]
    else:
        return d
