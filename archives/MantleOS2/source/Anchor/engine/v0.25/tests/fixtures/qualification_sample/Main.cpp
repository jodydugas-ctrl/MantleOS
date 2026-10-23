#include <QAction>
#include <QFile>
#include <QFileInfo>
#include <QMenu>
#include <QProcess>
#include <QSettings>
#include <QPluginLoader>
#include <QShortcut>
#include <QtConcurrent>
#include <QFutureWatcher>

void Controller::wire() {
    connect(ui->actionSave, &QAction::triggered, this, &Controller::saveCurrent);
    auto dynamicAction = new QAction("Dynamic", this);
    menu->addAction(dynamicAction);
    auto shortcut = new QShortcut(QKeySequence("Ctrl+Shift+K"), this);
    connect(shortcut, &QShortcut::activated, this, &Controller::backgroundTask);
}

void Controller::saveCurrent() {
    QFile output("state.bin");
    output.write("x");
    QSettings settings;
    settings.setValue("lastSave", "state.bin");
    QFileInfo info("state.bin");
    if (info.isWritable()) {
        QProcess::startDetached("helper", {});
    }
}

void Controller::backgroundTask() {
    auto future = QtConcurrent::run([this]() { saveCurrent(); });
    watcher.setFuture(future);
    connect(&watcher, &QFutureWatcher<void>::finished, this, &Controller::finished);
}

void Controller::pluginProbe() {
    QPluginLoader loader("optional-plugin");
    loader.load();
}
