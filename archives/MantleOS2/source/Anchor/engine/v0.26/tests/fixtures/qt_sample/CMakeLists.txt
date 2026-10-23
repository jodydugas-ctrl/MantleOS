find_package(Qt6 REQUIRED COMPONENTS Widgets)
add_executable(sample MainWindow.cpp)
target_link_libraries(sample PRIVATE Qt6::Widgets)
