MAX_PROFILE_PHOTO_SIZE = 5 * 1024 * 1024
ALLOWED_PROFILE_PHOTO_FORMATS = {"JPEG", "PNG", "WEBP"}


def validate_profile_photo(uploaded_file):
    """Return an error message for unsafe/unsupported doctor profile images."""
    if not uploaded_file:
        return ""
    if uploaded_file.size > MAX_PROFILE_PHOTO_SIZE:
        return "Profile photo must be 5 MB or smaller."

    # Keep Django startup independent of Pillow, so a missing optional image
    # dependency does not prevent the whole site from loading. Image uploads
    # still fail safely with an actionable message until Pillow is installed.
    try:
        from PIL import Image, UnidentifiedImageError
    except ImportError:
        return "Image uploads are unavailable until Pillow is installed. Run: python -m pip install Pillow"

    try:
        with Image.open(uploaded_file) as image:
            if image.format not in ALLOWED_PROFILE_PHOTO_FORMATS:
                return "Upload a JPG, PNG, or WebP image."
            image.verify()
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
        return "The uploaded file is not a valid image."
    finally:
        uploaded_file.seek(0)
    return ""
