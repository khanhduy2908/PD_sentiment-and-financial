import yaml, os

def load_yaml(path):
    with open(os.path.join(os.path.dirname(os.path.dirname(__file__)), path), 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)
