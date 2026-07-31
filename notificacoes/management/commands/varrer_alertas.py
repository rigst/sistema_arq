from django.core.management.base import BaseCommand

from notificacoes.services import varrer_todas


class Command(BaseCommand):
    help = "Varre prazos, projetos parados, desvios de obra e obrigações, gerando notificações."

    def handle(self, *args, **options):
        total = varrer_todas()
        self.stdout.write(self.style.SUCCESS(f"Varredura concluída. Notificações criadas: {total}."))
