from pydantic import BaseModel

class UrlRequest(BaseModel):
    job_url: str