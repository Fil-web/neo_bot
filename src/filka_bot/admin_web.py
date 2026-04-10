from aiohttp import web

from filka_bot.services.analytics import AnalyticsService
from filka_bot.services.knowledge_base import KnowledgeBaseService
from filka_bot.services.user_profiles import UserProfileService


def build_admin_app(
    *,
    token: str,
    analytics: AnalyticsService,
    knowledge_base: KnowledgeBaseService,
    user_profiles: UserProfileService,
) -> web.Application:
    app = web.Application()

    def authorized(request: web.Request) -> bool:
        return request.query.get("token") == token

    async def dashboard(request: web.Request) -> web.Response:
        if not authorized(request):
            return web.Response(status=403, text="Forbidden")
        stats = analytics.get_admin_stats()
        kb_stats = knowledge_base.stats()
        users_count = len(user_profiles.list_user_ids("all"))
        html = f"""
        <html>
          <head>
            <title>Filka Admin</title>
            <style>
              body {{ font-family: sans-serif; margin: 40px; background: #f5f1e8; color: #1f1f1f; }}
              .card {{ background: white; border-radius: 12px; padding: 20px; margin-bottom: 16px; box-shadow: 0 6px 20px rgba(0,0,0,0.08); }}
              h1, h2 {{ margin-top: 0; }}
            </style>
          </head>
          <body>
            <h1>Filka Admin</h1>
            <div class="card">
              <h2>События</h2>
              <p>Сегодня событий: {stats.get('total_events_today', 0)}</p>
              <p>Уникальных пользователей: {stats.get('total_users', 0)}</p>
              <p>Активных сегодня: {stats.get('active_today', 0)}</p>
              <p>Ошибок сегодня: {stats.get('errors_today', 0)}</p>
            </div>
            <div class="card">
              <h2>Пользователи</h2>
              <p>Всего профилей: {users_count}</p>
            </div>
            <div class="card">
              <h2>База знаний</h2>
              <p>Документов: {kb_stats.get('documents', 0)}</p>
              <p>Чанков: {kb_stats.get('chunks', 0)}</p>
              <p>Embeddings: {kb_stats.get('embedded_chunks', 0)}</p>
            </div>
          </body>
        </html>
        """
        return web.Response(text=html, content_type="text/html")

    app.router.add_get("/admin", dashboard)
    return app
