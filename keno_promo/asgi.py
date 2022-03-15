import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'keno_promo.settings')
django_asgi_app = get_asgi_application()



from channels.auth import AuthMiddlewareStack
import jogo.routing


application = ProtocolTypeRouter({
  "http": django_asgi_app,
  "websocket": AuthMiddlewareStack(
    URLRouter(
      jogo.routing.websocket_urlpatterns
    )
  )
})