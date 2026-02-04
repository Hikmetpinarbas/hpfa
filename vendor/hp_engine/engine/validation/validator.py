import jsonschema
import json
import os
from typing import Dict, List

class HPContractValidator:
    """
    HP Engine Anayasa Denetleyicisi.
    Şemaları (Schemas) kullanarak veri ve hüküm hijyenini denetler.
    """
    def __init__(self, schema_dir: str = "canon/contracts/schemas"):
        self.schema_dir = schema_dir
        self.schemas = self._load_all_schemas()

    def _load_all_schemas(self) -> Dict:
        schemas = {}
        for filename in os.listdir(self.schema_dir):
            if filename.endswith(".schema.json"):
                with open(os.path.join(self.schema_dir, filename), 'r') as f:
                    schema_data = json.load(f)
                    schemas[schema_data["$id"]] = schema_data
        return schemas

    def validate(self, instance: Dict, schema_id: str):
        """Veriyi ilgili şemaya göre valide eder."""
        try:
            jsonschema.validate(instance=instance, schema=self.schemas[schema_id])
            return True, "Valid"
        except jsonschema.ValidationError as e:
            return False, e.message
