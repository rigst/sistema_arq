"""Testes do verificador de lock.

scripts/conferir_lock.py é um portão de CI: ele impede que requirements.txt e
requirements.lock divirjam depois de um bump do Dependabot. Portão que quebra
em silêncio é pior do que portão nenhum — se o script passar a devolver 0
sempre, ninguém percebe até a imagem instalar a versão errada.
"""

import importlib.util
import tempfile
from pathlib import Path

from django.test import SimpleTestCase

RAIZ = Path(__file__).resolve().parent.parent
SCRIPT = RAIZ / "scripts" / "conferir_lock.py"


def carregar(requirements, lock):
    """Importa o script apontando-o para arquivos de teste."""
    spec = importlib.util.spec_from_file_location("conferir_lock_sob_teste", SCRIPT)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    modulo.REQUISITOS = requirements
    modulo.LOCK = lock
    return modulo


class ConferirLockTests(SimpleTestCase):
    def setUp(self):
        self.dir = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.req = self.dir / "requirements.txt"
        self.lock = self.dir / "requirements.lock"

    def _rodar(self, requirements, lock):
        self.req.write_text(requirements, encoding="utf-8")
        self.lock.write_text(lock, encoding="utf-8")
        return carregar(self.req, self.lock).main()

    def test_aprova_quando_as_versoes_conferem(self):
        codigo = self._rodar(
            "Django==6.1\npsycopg[binary]==3.2.12\n",
            "django==6.1 \\\n    --hash=sha256:abc\npsycopg==3.2.12 \\\n    --hash=sha256:def\n",
        )
        self.assertEqual(codigo, 0)

    def test_reprova_quando_a_versao_diverge(self):
        codigo = self._rodar(
            "Django==6.2\n",
            "django==6.1 \\\n    --hash=sha256:abc\n",
        )
        self.assertEqual(codigo, 1)

    def test_reprova_quando_falta_no_lock(self):
        codigo = self._rodar(
            "Django==6.1\nredis==5.2.1\n",
            "django==6.1 \\\n    --hash=sha256:abc\n",
        )
        self.assertEqual(codigo, 1)

    def test_ignora_comentario_e_linha_vazia(self):
        codigo = self._rodar(
            "# comentário\n\nDjango==6.1\n",
            "django==6.1 \\\n    --hash=sha256:abc\n",
        )
        self.assertEqual(codigo, 0)

    def test_normaliza_underscore_e_caixa(self):
        # O PyPI trata "-" e "_" como o mesmo nome; o lock sai normalizado.
        codigo = self._rodar(
            "dj_database_url==3.1.2\n",
            "dj-database-url==3.1.2 \\\n    --hash=sha256:abc\n",
        )
        self.assertEqual(codigo, 0)

    def test_reprova_quando_o_lock_nao_existe(self):
        self.req.write_text("Django==6.1\n", encoding="utf-8")
        ausente = self.dir / "nao-existe.lock"
        self.assertEqual(carregar(self.req, ausente).main(), 1)

    def test_o_lock_do_projeto_esta_em_dia(self):
        # Roda o script de verdade contra os arquivos versionados.
        modulo = carregar(RAIZ / "requirements.txt", RAIZ / "requirements.lock")
        self.assertEqual(modulo.main(), 0)
