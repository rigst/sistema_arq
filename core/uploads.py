from pathlib import Path

from django.core.exceptions import ValidationError


DOCUMENT_EXTENSIONS = {
    "csv", "doc", "docx", "dwg", "dxf", "ifc", "jpeg", "jpg", "ods", "odt",
    "ofx", "pdf", "png", "ppt", "pptx", "rtf", "txt", "webp", "xls", "xlsx", "zip",
}
IMAGE_EXTENSIONS = {"jpeg", "jpg", "png", "webp"}
MAX_DOCUMENT_SIZE = 25 * 1024 * 1024
MAX_IMAGE_SIZE = 10 * 1024 * 1024


def _validar_upload(arquivo, extensoes, tamanho_max, rotulo):
    extensao = Path(arquivo.name or "").suffix.lower().removeprefix(".")
    if extensao not in extensoes:
        permitidas = ", ".join(sorted(extensoes))
        raise ValidationError(f"Formato não permitido para {rotulo}. Use: {permitidas}.")
    if arquivo.size > tamanho_max:
        limite_mb = tamanho_max // (1024 * 1024)
        raise ValidationError(f"O arquivo excede o limite de {limite_mb} MB.")


def validar_documento(arquivo):
    _validar_upload(arquivo, DOCUMENT_EXTENSIONS, MAX_DOCUMENT_SIZE, "documento")


def validar_imagem(arquivo):
    _validar_upload(arquivo, IMAGE_EXTENSIONS, MAX_IMAGE_SIZE, "imagem")


def validar_extrato(arquivo):
    _validar_upload(arquivo, {"csv", "ofx"}, 5 * 1024 * 1024, "extrato")
