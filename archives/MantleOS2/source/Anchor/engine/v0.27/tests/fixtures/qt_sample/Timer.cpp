#include <QTimer>
void App::makeWindow() {
    connect(&checkpointTimer, &QTimer::timeout, this, &App::checkpoint);
    checkpointTimer.start(60 * 1000);
    connect(window, &Window::activated, this, [this](Editor *editor) {
        remember(editor);
    });
}
