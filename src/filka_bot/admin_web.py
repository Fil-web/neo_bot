from html import escape

from aiohttp import web
from aiogram import Bot

from filka_bot.services.analytics import AnalyticsService
from filka_bot.services.knowledge_base import KnowledgeBaseService
from filka_bot.services.moderation import ModerationService
from filka_bot.services.user_profiles import UserProfileService


def _layout(title: str, token: str, body: str) -> str:
    nav = f"""
    <nav class="nav">
      <a href="/admin?token={token}">Dashboard</a>
      <a href="/admin/users?token={token}">Users</a>
      <a href="/admin/events?token={token}">Events</a>
      <a href="/admin/knowledge?token={token}">Knowledge</a>
      <a href="/admin/broadcast?token={token}">Broadcast</a>
    </nav>
    """
    return f"""
    <html>
      <head>
        <title>{escape(title)}</title>
        <style>
          body {{ font-family: sans-serif; margin: 0; background: #f3ede2; color: #1e1e1e; }}
          .page {{ max-width: 1200px; margin: 0 auto; padding: 28px; }}
          .nav {{ display: flex; gap: 16px; margin-bottom: 24px; flex-wrap: wrap; }}
          .nav a {{ text-decoration: none; color: #1e1e1e; background: #fff; padding: 10px 14px; border-radius: 10px; }}
          .card {{ background: #fff; border-radius: 16px; padding: 20px; margin-bottom: 18px; box-shadow: 0 10px 30px rgba(0,0,0,0.08); }}
          .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; }}
          table {{ width: 100%; border-collapse: collapse; }}
          th, td {{ text-align: left; padding: 10px; border-bottom: 1px solid #e7dfd1; vertical-align: top; }}
          th {{ background: #faf6ef; }}
          .muted {{ color: #6b655d; font-size: 14px; }}
          .badge {{ display: inline-block; padding: 4px 8px; border-radius: 999px; background: #efe5d2; }}
          form.inline {{ display: inline; }}
          input, select, textarea, button {{ font: inherit; padding: 10px 12px; border-radius: 10px; border: 1px solid #d7cfbf; width: 100%; box-sizing: border-box; }}
          textarea {{ min-height: 120px; resize: vertical; }}
          button {{ background: #1f1f1f; color: white; cursor: pointer; width: auto; }}
          .row {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; margin-bottom: 12px; }}
          .danger {{ background: #8a2d2d; }}
          pre {{ white-space: pre-wrap; background: #faf6ef; padding: 12px; border-radius: 10px; }}
        </style>
      </head>
      <body>
        <div class="page">
          <h1>{escape(title)}</h1>
          {nav}
          {body}
        </div>
      </body>
    </html>
    """


def _auth_ok(request: web.Request, token: str) -> bool:
    return request.query.get("token") == token


def _redirect(path: str, token: str) -> web.Response:
    raise web.HTTPFound(f"{path}?token={token}")


def build_admin_app(
    *,
    token: str,
    bot: Bot,
    analytics: AnalyticsService,
    knowledge_base: KnowledgeBaseService,
    moderation: ModerationService,
    user_profiles: UserProfileService,
) -> web.Application:
    app = web.Application()

    async def dashboard(request: web.Request) -> web.Response:
        if not _auth_ok(request, token):
            return web.Response(status=403, text="Forbidden")
        stats = analytics.get_admin_stats()
        kb_stats = knowledge_base.stats()
        users_count = len(user_profiles.list_user_ids("all"))
        body = f"""
        <div class="grid">
          <div class="card"><h3>Events Today</h3><p>{stats.get('total_events_today', 0)}</p></div>
          <div class="card"><h3>Users Total</h3><p>{stats.get('total_users', 0)}</p></div>
          <div class="card"><h3>Active Today</h3><p>{stats.get('active_today', 0)}</p></div>
          <div class="card"><h3>Errors Today</h3><p>{stats.get('errors_today', 0)}</p></div>
          <div class="card"><h3>User Profiles</h3><p>{users_count}</p></div>
          <div class="card"><h3>KB Documents</h3><p>{kb_stats.get('documents', 0)}</p></div>
          <div class="card"><h3>KB Chunks</h3><p>{kb_stats.get('chunks', 0)}</p></div>
          <div class="card"><h3>KB Embeddings</h3><p>{kb_stats.get('embedded_chunks', 0)}</p></div>
        </div>
        """
        return web.Response(text=_layout("Filka Admin", token, body), content_type="text/html")

    async def users_page(request: web.Request) -> web.Response:
        if not _auth_ok(request, token):
            return web.Response(status=403, text="Forbidden")
        segment = request.query.get("segment", "all")
        users = user_profiles.list_users(segment=segment, limit=300)
        rows = "".join(
            f"""
            <tr>
              <td>{escape(user['user_id'])}</td>
              <td>{escape(user['username'])}</td>
              <td>{escape(user['first_name'])}</td>
              <td>{escape(user['mode'])}</td>
              <td>{escape(user['admin_mode'])}</td>
              <td>{escape(user['last_seen_at'])}</td>
              <td>
                <form class="inline" method="post" action="/admin/users/action?token={escape(token)}">
                  <input type="hidden" name="user_id" value="{escape(user['user_id'])}" />
                  <input type="hidden" name="action" value="ban" />
                  <button class="danger" type="submit">Ban</button>
                </form>
                <form class="inline" method="post" action="/admin/users/action?token={escape(token)}">
                  <input type="hidden" name="user_id" value="{escape(user['user_id'])}" />
                  <input type="hidden" name="action" value="unban" />
                  <button type="submit">Unban</button>
                </form>
                <form class="inline" method="post" action="/admin/users/action?token={escape(token)}">
                  <input type="hidden" name="user_id" value="{escape(user['user_id'])}" />
                  <input type="hidden" name="action" value="mute" />
                  <input type="hidden" name="minutes" value="30" />
                  <button type="submit">Mute 30m</button>
                </form>
              </td>
            </tr>
            """
            for user in users
        )
        body = f"""
        <div class="card">
          <form method="get" action="/admin/users">
            <input type="hidden" name="token" value="{escape(token)}" />
            <div class="row">
              <div>
                <label>Segment</label>
                <select name="segment">
                  <option value="all">all</option>
                  <option value="active_today">active_today</option>
                  <option value="admin_mode">admin_mode</option>
                  <option value="mode:default">mode:default</option>
                  <option value="mode:hard">mode:hard</option>
                  <option value="mode:business">mode:business</option>
                  <option value="mode:sales">mode:sales</option>
                  <option value="mode:support">mode:support</option>
                </select>
              </div>
              <div><label>&nbsp;</label><button type="submit">Filter</button></div>
            </div>
          </form>
        </div>
        <div class="card">
          <table>
            <thead><tr><th>User ID</th><th>Username</th><th>Name</th><th>Mode</th><th>Admin mode</th><th>Last seen</th><th>Actions</th></tr></thead>
            <tbody>{rows}</tbody>
          </table>
        </div>
        """
        return web.Response(text=_layout("Users", token, body), content_type="text/html")

    async def events_page(request: web.Request) -> web.Response:
        if not _auth_ok(request, token):
            return web.Response(status=403, text="Forbidden")
        event_type = request.query.get("event_type", "")
        success = request.query.get("success", "")
        rows = analytics.recent_events(limit=300, event_type=event_type, success=success)
        table_rows = "".join(
            f"""
            <tr>
              <td>{escape(row['created_at'])}</td>
              <td>{escape(row['user_id'])}</td>
              <td>{escape(row['event_type'])}</td>
              <td>{escape(row['success'])}</td>
              <td>{escape(row['details'])}</td>
            </tr>
            """
            for row in rows
        )
        body = f"""
        <div class="card">
          <form method="get" action="/admin/events">
            <input type="hidden" name="token" value="{escape(token)}" />
            <div class="row">
              <div><label>Event type</label><input name="event_type" value="{escape(event_type)}" /></div>
              <div>
                <label>Success</label>
                <select name="success">
                  <option value="">all</option>
                  <option value="1">1</option>
                  <option value="0">0</option>
                </select>
              </div>
              <div><label>&nbsp;</label><button type="submit">Filter</button></div>
            </div>
          </form>
        </div>
        <div class="card">
          <table>
            <thead><tr><th>Created</th><th>User ID</th><th>Type</th><th>Success</th><th>Details</th></tr></thead>
            <tbody>{table_rows}</tbody>
          </table>
        </div>
        """
        return web.Response(text=_layout("Events", token, body), content_type="text/html")

    async def knowledge_page(request: web.Request) -> web.Response:
        if not _auth_ok(request, token):
            return web.Response(status=403, text="Forbidden")
        docs = knowledge_base.list_documents(limit=300)
        rows = "".join(
            f"""
            <tr>
              <td>{escape(doc['id'])}</td>
              <td><a href="/admin/knowledge/{escape(doc['id'])}?token={escape(token)}">{escape(doc['title'])}</a></td>
              <td>{escape(doc['source_type'])}</td>
              <td>{escape(doc['source_ref'])}</td>
              <td>{escape(doc['created_at'])}</td>
              <td>
                <form class="inline" method="post" action="/admin/knowledge/{escape(doc['id'])}/delete?token={escape(token)}">
                  <button class="danger" type="submit">Delete</button>
                </form>
              </td>
            </tr>
            """
            for doc in docs
        )
        body = f"""
        <div class="card">
          <table>
            <thead><tr><th>ID</th><th>Title</th><th>Source</th><th>Ref</th><th>Created</th><th>Action</th></tr></thead>
            <tbody>{rows}</tbody>
          </table>
        </div>
        """
        return web.Response(text=_layout("Knowledge Base", token, body), content_type="text/html")

    async def knowledge_detail(request: web.Request) -> web.Response:
        if not _auth_ok(request, token):
            return web.Response(status=403, text="Forbidden")
        document_id = int(request.match_info["document_id"])
        doc = knowledge_base.get_document(document_id)
        if not doc:
            return web.Response(status=404, text="Not found")
        chunks_html = "".join(
            f'<div class="card"><h3>Chunk {escape(chunk["index"])}</h3><pre>{escape(chunk["content"])}</pre></div>'
            for chunk in doc["chunks"]
        )
        body = f"""
        <div class="card">
          <p><strong>Title:</strong> {escape(doc['title'])}</p>
          <p><strong>Source type:</strong> {escape(doc['source_type'])}</p>
          <p><strong>Source ref:</strong> {escape(doc['source_ref'])}</p>
          <p><strong>Added by:</strong> {escape(doc['added_by'])}</p>
          <p><strong>Created:</strong> {escape(doc['created_at'])}</p>
        </div>
        {chunks_html}
        """
        return web.Response(text=_layout(f"KB Document {document_id}", token, body), content_type="text/html")

    async def knowledge_delete(request: web.Request) -> web.Response:
        if not _auth_ok(request, token):
            return web.Response(status=403, text="Forbidden")
        document_id = int(request.match_info["document_id"])
        knowledge_base.delete_document(document_id)
        return _redirect("/admin/knowledge", token)

    async def broadcast_page(request: web.Request) -> web.Response:
        if not _auth_ok(request, token):
            return web.Response(status=403, text="Forbidden")
        body = f"""
        <div class="card">
          <form method="post" action="/admin/broadcast?token={escape(token)}">
            <div class="row">
              <div>
                <label>Segment</label>
                <select name="segment">
                  <option value="all">all</option>
                  <option value="active_today">active_today</option>
                  <option value="admin_mode">admin_mode</option>
                  <option value="mode:default">mode:default</option>
                  <option value="mode:hard">mode:hard</option>
                  <option value="mode:business">mode:business</option>
                  <option value="mode:sales">mode:sales</option>
                  <option value="mode:support">mode:support</option>
                </select>
              </div>
            </div>
            <div>
              <label>Message</label>
              <textarea name="message"></textarea>
            </div>
            <div style="margin-top:12px;">
              <button type="submit">Send broadcast</button>
            </div>
          </form>
        </div>
        """
        return web.Response(text=_layout("Broadcast", token, body), content_type="text/html")

    async def broadcast_send(request: web.Request) -> web.Response:
        if not _auth_ok(request, token):
            return web.Response(status=403, text="Forbidden")
        form = await request.post()
        segment = str(form.get("segment", "all")).strip()
        message = str(form.get("message", "")).strip()
        recipients = user_profiles.list_user_ids(segment)
        sent = 0
        failed = 0
        for user_id in recipients:
            try:
                await bot.send_message(user_id, message)
                sent += 1
            except Exception:
                failed += 1
        analytics.log_event("broadcast", success=True, details=f"web;segment:{segment};sent:{sent};failed:{failed}")
        body = f"""
        <div class="card">
          <p>Broadcast sent.</p>
          <p>Segment: <span class="badge">{escape(segment)}</span></p>
          <p>Sent: {sent}</p>
          <p>Failed: {failed}</p>
          <p><a href="/admin/broadcast?token={escape(token)}">Back</a></p>
        </div>
        """
        return web.Response(text=_layout("Broadcast Result", token, body), content_type="text/html")

    async def user_action(request: web.Request) -> web.Response:
        if not _auth_ok(request, token):
            return web.Response(status=403, text="Forbidden")
        form = await request.post()
        user_id = int(form.get("user_id", "0"))
        action = str(form.get("action", "")).strip()
        reason = str(form.get("reason", "")).strip()
        minutes = int(form.get("minutes", "30") or "30")
        if action == "ban":
            moderation.ban(user_id, reason=reason)
        elif action == "mute":
            moderation.mute(user_id, minutes=minutes, reason=reason)
        elif action == "unban":
            moderation.unban(user_id)
        analytics.log_event("moderation", user_id=user_id, success=True, details=f"web:{action}")
        return _redirect("/admin/users", token)

    app.router.add_get("/admin", dashboard)
    app.router.add_get("/admin/users", users_page)
    app.router.add_post("/admin/users/action", user_action)
    app.router.add_get("/admin/events", events_page)
    app.router.add_get("/admin/knowledge", knowledge_page)
    app.router.add_get("/admin/knowledge/{document_id}", knowledge_detail)
    app.router.add_post("/admin/knowledge/{document_id}/delete", knowledge_delete)
    app.router.add_get("/admin/broadcast", broadcast_page)
    app.router.add_post("/admin/broadcast", broadcast_send)
    return app
