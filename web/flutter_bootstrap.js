{{flutter_js}}
{{flutter_build_config}}

// No serviceWorkerSettings: Flutter's own (deprecated) flutter_service_worker.js would take over
// the scope of web/service-worker.js, unregister it and reload the page.
_flutter.loader.load();
