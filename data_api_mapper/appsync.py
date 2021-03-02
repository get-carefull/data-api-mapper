import re
from typing import List, Dict


class AppsyncEvent:

    def __init__(self, event) -> None:
        self.event = event
        self.info = event['info']
        self.arguments = self.event['arguments']
        self.username = self.event['identity']['username']
        self.name = self.event['identity']['claims'].get('name', None)
        self.email = self.event['identity']['claims'].get('email', None)

    @property
    def selection_set_list(self) -> List[str]:
        return self.info['selectionSetList']

    @property
    def selection_set_graphql(self) -> str:
        return self.info['selectionSetGraphQL']

    @property
    def parent_type_name(self) -> str:
        return self.info['parentTypeName']

    @property
    def field_name(self) -> str:
        return self.info['fieldName']

    @property
    def variables(self) -> Dict:
        return self.info['variables']

    def get_argument(self, key: str, default=''):
        return self.arguments.get(key, default)


class CamelSnakeConverter:
    @staticmethod
    def to_snake(camel):
        return [re.sub(r'(?<!^)(?=[A-Z])', '_', x).lower() for x in camel]

    @classmethod
    def dict_to_camel(cls, value):
        if isinstance(value, dict):
            return {cls.to_camel(x): cls.dict_to_camel(value[x]) for x in value.keys()}
        if isinstance(value, list):
            return [cls.dict_to_camel(x) for x in value]
        return value

    @classmethod
    def to_camel(cls, snake_str):
        components = snake_str.split('_')
        return components[0] + ''.join(x.title() for x in components[1:])



