find_package(Qt6 REQUIRED COMPONENTS Widgets Network Concurrent)
add_executable(qualification Main.cpp)
target_link_libraries(qualification PRIVATE Qt6::Widgets Qt6::Network Qt6::Concurrent)
