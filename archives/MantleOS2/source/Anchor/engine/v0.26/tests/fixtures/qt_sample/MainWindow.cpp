#include <QFile>
#include <QProcess>
void MainWindow::wire() {
    connect(ui->actionSave, &QAction::triggered, this, &MainWindow::saveCurrentFile);
    connectEditorAction(ui->actionSave, &ScintillaNext::save);
    auto a = new QAction("Dynamic", this);
    menu->addAction(a);
#ifdef Q_OS_WIN
    QProcess::startDetached("cmd", {"/c", "echo"});
#endif
}
