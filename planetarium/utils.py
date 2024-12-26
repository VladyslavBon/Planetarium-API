import pathlib
import uuid

from django.utils.text import slugify


def image_file_path(instance, filename):
    filename = (
        f"{slugify(instance.title)}-{uuid.uuid4()}" + pathlib.Path(filename).suffix
    )
    return pathlib.Path("uploads/astronomy_show/") / pathlib.Path(filename)
