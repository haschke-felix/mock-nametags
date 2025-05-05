from pydantic import BaseModel

from src.params import Params


class Instruction(BaseModel):
    vehicle: str
    value: bool


class Person(BaseModel):
    first_name: str
    last_name: str
    personnel_id: str | None
    image_url: str | None
    function: str | None
    qualifications: dict[str, bool]
    instructions: list[Instruction]

    @classmethod
    def from_json(cls, data: dict):
        qualifications_dict = {key: key in data["qualifications"] for key in
                               Params.all_technical_qualifications + Params.all_leading_qualifications}
        return cls(
            first_name=data["first_name"],
            last_name=data["last_name"],
            personnel_id=data["personnel_id"],
            image_url=data["image_url"],
            function=data["function"],
            qualifications=qualifications_dict,
            instructions=[Instruction(**instr) for instr in data["instructions"]],

        )
