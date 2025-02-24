{
    "application": False,
    "assets": {
        "web.assets_backend": ["zbsync/static/src/list_renderer.js"],
        "web.assets_qweb": [],
    },
    "author": "Marc Wimmer (marc@itewimmer.de)",
    "css": [],
    "data": [
        "security/groups.xml",
        "data/base_elements.xml",
        "data/cronjobs.xml",
        "data/sequence.xml",
        "views/assets.xml",
        "views/batch.xml",
        "views/cronstarts.xml",
        "views/debugger_form.xml",
        "views/domain_form.xml",
        "views/instance.xml",
        "views/log_view.xml",
        "views/pipeline.xml",
        "views/worker_form.xml",
        "views/worker_instanceenvdumper.xml",
        "views/worker_start_form.xml",
        "views/worker_stop_form.xml",
        "views/worker_transformer.xml",
        "views/worker_trigger_form.xml",
        "wizard/wiz_new_el.xml",
        "views/menu.xml",
        "security/ir.model.access.csv",
    ],
    "demo": [],
    "depends": ["mail", "zbsync_xport"],
    "external_dependencies": {"bin": [], "python": ["arrow", "faker"]},
    "name": "zbsync",
    "qweb": [],
    "test": [],
    "version": "1.2",
}
