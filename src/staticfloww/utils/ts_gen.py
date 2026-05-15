from typing import Any, Dict, List, Optional, Type, Union, get_args, get_origin
from pydantic import BaseModel
import inspect

class TSGenerator:
    """
    A utility to generate TypeScript interfaces from Pydantic models.
    """
    def __init__(self):
        self.seen_models = set()
        self.output = []

    def generate(self, model: Type[BaseModel]) -> str:
        self.seen_models = set()
        self.output = []
        self._process_model(model)
        return "\n\n".join(reversed(self.output))

    def _process_model(self, model: Type[BaseModel]):
        if model in self.seen_models:
            return
        self.seen_models.add(model)

        name = model.__name__
        lines = [f"export interface {name} {{"]
        
        for field_name, field in model.model_fields.items():
            # Use the alias (e.g., 'type') if available, otherwise use the field name
            ts_field_name = field.alias if field.alias else field_name
            ts_type = self._get_ts_type(field.annotation)
            optional = not field.is_required()
            lines.append(f"  {ts_field_name}{'?' if optional else ''}: {ts_type};")
        
        lines.append("}")
        self.output.append("\n".join(lines))

    def _get_ts_type(self, py_type: Any) -> str:
        origin = get_origin(py_type)
        args = get_args(py_type)

        if py_type == str:
            return "string"
        if py_type in (int, float):
            return "number"
        if py_type == bool:
            return "boolean"
        if py_type in (dict, Any):
            return "any"
        
        # Handle Optional/Union
        if origin is Union:
            # Filter out NoneType for the base type
            non_none_args = [arg for arg in args if arg != type(None)]
            if len(non_none_args) == 1:
                return self._get_ts_type(non_none_args[0])
            return " | ".join([self._get_ts_type(arg) for arg in non_none_args])

        # Handle List
        if origin in (list, List):
            return f"{self._get_ts_type(args[0])}[]"

        # Handle Nested Pydantic Models
        if inspect.isclass(py_type) and issubclass(py_type, BaseModel):
            self._process_model(py_type)
            return py_type.__name__

        return "any"

def generate_typescript(model: Type[BaseModel]) -> str:
    """
    Helper function to generate TS types from a Pydantic model.
    """
    return TSGenerator().generate(model)
