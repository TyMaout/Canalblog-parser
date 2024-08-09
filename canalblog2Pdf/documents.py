from datetime import datetime

from dataclasses import dataclass, field
from dataclasses_json import dataclass_json, config, Undefined
from marshmallow import fields

@dataclass_json
@dataclass
class Commentaire:
    id:str = field(default=None)
    auteur: str = field(default=None)
    date: datetime = field(
        default=None, metadata=config(encoder=datetime.isoformat, decoder=datetime.fromisoformat, mm_field= fields.DateTime(format='iso')))
    content: str = field(default=None)

@dataclass_json
@dataclass
class Article:
    id:str = field(default=None)
    date: datetime = field(
        default=None, metadata=config(encoder=datetime.isoformat, decoder=datetime.fromisoformat, mm_field= fields.DateTime(format='iso')))
    title: str = field(default=None)
    body: str = field(default=None)
    categorie: list[str] = field(default_factory=list)
    commentaires: list['Commentaire'] = field(default_factory=list)

    def __post_init__(self) -> None:
        
        if self.commentaires is None:
            self.commentaires = []

        comments:list['Commentaire'] = []
        for comment in self.commentaires:
            comments.append(Commentaire(**comment))
        self.commentaires = comments