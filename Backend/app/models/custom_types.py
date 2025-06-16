# app/models/custom_types.py

from pydantic import BaseModel
from pydantic_core import CoreSchema, core_schema, PydanticCustomError
from typing import Any, Callable, Dict
from shapely.geometry import Point

class PointInResponse(BaseModel):
    latitude: float
    longitude: float

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type: Any, handler: Callable[[Any], CoreSchema]) -> CoreSchema:
        # Esta función convierte un objeto Shapely Point a una instancia de PointInResponse.
        # Es para cuando el dato de origen es un objeto Point de Shapely (ej. desde el ORM).
        def validate_point_object(value: Any) -> 'PointInResponse':
            if isinstance(value, Point):
                return cls(latitude=value.y, longitude=value.x)
            raise PydanticCustomError('expected_shapely_point', 'Expected a Shapely Point object for PointInResponse')

        # 1. Esquema para la validación del modelo `PointInResponse` en sí mismo.
        # Esto maneja la entrada de diccionarios (JSON) que ya tienen 'latitude' y 'longitude'.
        # `handler(cls)` le dice a Pydantic que genere el esquema predeterminado para este BaseModel.
        model_validation_schema = handler(cls)

        # 2. Esquema para la validación de objetos `shapely.geometry.Point`.
        # Esto usará nuestra función `validate_point_object` para convertir el Shapely Point.
        point_object_validation_schema = core_schema.no_info_after_validator_function(
            validate_point_object,
            core_schema.is_instance_schema(Point) # Espera una instancia de shapely.geometry.Point
        )

        # 3. Esquema de Unión para la validación de entrada (parsing).
        # Permite que la entrada sea un diccionario (manejado por model_validation_schema)
        # O un objeto Shapely Point (manejado por point_object_validation_schema).
        validation_schema = core_schema.union_schema([
            model_validation_schema,
            point_object_validation_schema,
        ])

        # 4. Función para la serialización de una instancia de `PointInResponse` a un diccionario.
        # Esto es para cuando FastAPI convierte el objeto Python a JSON en la respuesta.
        def serialize_point_in_response(obj: 'PointInResponse') -> Dict[str, float]:
            # La instancia ya es un PointInResponse, así que simplemente extraemos sus atributos
            return {'latitude': obj.latitude, 'longitude': obj.longitude}

        # Definimos el esquema final que Pydantic usará para este tipo.
        return core_schema.json_or_python_schema(
            json_schema=validation_schema,  # Cómo validar desde JSON (dict o Point)
            python_schema=validation_schema, # Cómo validar desde Python (dict o Point)
            serialization=core_schema.plain_serializer_function_ser_schema(
                serialize_point_in_response,
                info_arg=False,
            )
        )