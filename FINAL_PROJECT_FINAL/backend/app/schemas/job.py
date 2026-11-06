from pydantic import BaseModel

class JobRequest(BaseModel):
    text: str