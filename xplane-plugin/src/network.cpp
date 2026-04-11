/*
 * ISFP Connect - Network Manager (TCP Server)
 * X-Plane plugin acts as server, Python app connects as client
 */

#include "isfp_plugin.h"
#include <sstream>
#include <iomanip>

namespace ISFP {

NetworkManager::NetworkManager()
    : listen_socket_(INVALID_SOCKET)
    , client_socket_(INVALID_SOCKET)
    , server_running_(false)
    , client_connected_(false)
    , port_(DEFAULT_PORT)
    , wsa_initialized_(false) {
}

NetworkManager::~NetworkManager() {
    Shutdown();
}

bool NetworkManager::Initialize() {
    int result = WSAStartup(MAKEWORD(2, 2), &wsa_data_);
    if (result != 0) {
        XPLMDebugString("ISFP Connect: WSAStartup failed\n");
        return false;
    }

    wsa_initialized_ = true;
    XPLMDebugString("ISFP Connect: Network manager initialized\n");
    return true;
}

void NetworkManager::Shutdown() {
    StopServer();

    if (wsa_initialized_) {
        WSACleanup();
        wsa_initialized_ = false;
    }

    XPLMDebugString("ISFP Connect: Network manager shutdown\n");
}

bool NetworkManager::StartServer(int port) {
    std::lock_guard<std::mutex> lock(socket_mutex_);

    if (server_running_) {
        return true;
    }

    port_ = port;

    // Create listen socket
    listen_socket_ = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    if (listen_socket_ == INVALID_SOCKET) {
        XPLMDebugString("ISFP Connect: Failed to create listen socket\n");
        return false;
    }

    // Allow reuse of address
    int reuse = 1;
    setsockopt(listen_socket_, SOL_SOCKET, SO_REUSEADDR, (char*)&reuse, sizeof(reuse));

    // Bind to port
    sockaddr_in addr;
    addr.sin_family = AF_INET;
    addr.sin_port = htons(port);
    addr.sin_addr.s_addr = INADDR_ANY;  // Listen on all interfaces

    if (bind(listen_socket_, (sockaddr*)&addr, sizeof(addr)) == SOCKET_ERROR) {
        XPLMDebugString("ISFP Connect: Failed to bind socket\n");
        closesocket(listen_socket_);
        listen_socket_ = INVALID_SOCKET;
        return false;
    }

    // Start listening
    if (listen(listen_socket_, 1) == SOCKET_ERROR) {
        XPLMDebugString("ISFP Connect: Failed to listen\n");
        closesocket(listen_socket_);
        listen_socket_ = INVALID_SOCKET;
        return false;
    }

    server_running_ = true;

    // Start server thread
    server_thread_ = std::thread(&NetworkManager::ServerLoop, this);

    std::string msg = "ISFP Connect: Server started on port " + std::to_string(port) + "\n";
    XPLMDebugString(msg.c_str());

    return true;
}

void NetworkManager::StopServer() {
    server_running_ = false;
    client_connected_ = false;

    // Close client socket
    if (client_socket_ != INVALID_SOCKET) {
        closesocket(client_socket_);
        client_socket_ = INVALID_SOCKET;
    }

    // Close listen socket
    if (listen_socket_ != INVALID_SOCKET) {
        closesocket(listen_socket_);
        listen_socket_ = INVALID_SOCKET;
    }

    // Wait for server thread
    if (server_thread_.joinable()) {
        server_thread_.detach();  // Don't block, just detach
    }

    XPLMDebugString("ISFP Connect: Server stopped\n");
}

void NetworkManager::ServerLoop() {
    XPLMDebugString("ISFP Connect: Server loop started\n");

    while (server_running_) {
        // Check for incoming connection (non-blocking)
        fd_set readfds;
        FD_ZERO(&readfds);
        FD_SET(listen_socket_, &readfds);

        timeval timeout;
        timeout.tv_sec = 1;
        timeout.tv_usec = 0;

        int result = select(0, &readfds, nullptr, nullptr, &timeout);

        if (result > 0 && FD_ISSET(listen_socket_, &readfds)) {
            // Accept new connection
            sockaddr_in client_addr;
            int addr_len = sizeof(client_addr);
            SOCKET new_client = accept(listen_socket_, (sockaddr*)&client_addr, &addr_len);

            if (new_client != INVALID_SOCKET) {
                std::lock_guard<std::mutex> lock(socket_mutex_);

                // Close old client if exists
                if (client_socket_ != INVALID_SOCKET) {
                    closesocket(client_socket_);
                }

                client_socket_ = new_client;
                client_connected_ = true;

                // Set TCP_NODELAY
                int nodelay = 1;
                setsockopt(client_socket_, IPPROTO_TCP, TCP_NODELAY, (char*)&nodelay, sizeof(nodelay));

                XPLMDebugString("ISFP Connect: Client connected\n");

                // Send welcome message
                std::string welcome = "{\"type\":\"connected\",\"version\":" + std::to_string(PLUGIN_VERSION) + "}\n";
                send(client_socket_, welcome.c_str(), (int)welcome.length(), 0);
            }
        }
    }

    XPLMDebugString("ISFP Connect: Server loop ended\n");
}

bool NetworkManager::SendData(const FlightData& data) {
    if (!client_connected_ || client_socket_ == INVALID_SOCKET) {
        return false;
    }

    // Build JSON
    std::ostringstream json;
    json << std::fixed << std::setprecision(6);
    json << "{";
    json << "\"type\":\"flight_data\",";
    json << "\"latitude\":" << data.latitude << ",";
    json << "\"longitude\":" << data.longitude << ",";
    json << "\"altitude\":" << data.altitude << ",";
    json << "\"elevation\":" << data.elevation << ",";
    json << "\"pitch\":" << data.pitch << ",";
    json << "\"roll\":" << data.roll << ",";
    json << "\"heading\":" << data.heading << ",";
    json << "\"indicated_airspeed\":" << data.indicated_airspeed << ",";
    json << "\"true_airspeed\":" << data.true_airspeed << ",";
    json << "\"groundspeed\":" << data.groundspeed << ",";
    json << "\"vertical_speed\":" << data.vertical_speed << ",";
    json << "\"altitude_msl\":" << data.altitude_msl << ",";
    json << "\"altitude_agl\":" << data.altitude_agl << ",";
    json << "\"mag_heading\":" << data.mag_heading << ",";
    json << "\"true_heading\":" << data.true_heading << ",";
    json << "\"com1_freq\":" << data.com1_freq << ",";
    json << "\"com2_freq\":" << data.com2_freq << ",";
    json << "\"transponder\":" << data.transponder << ",";
    json << "\"gear_deploy\":" << data.gear_deploy << ",";
    json << "\"flaps_ratio\":" << data.flaps_ratio << ",";
    json << "\"throttle_ratio\":" << data.throttle_ratio;
    json << "}\n";

    std::string data_str = json.str();

    std::lock_guard<std::mutex> lock(socket_mutex_);

    int sent = send(client_socket_, data_str.c_str(), (int)data_str.length(), 0);

    if (sent == SOCKET_ERROR) {
        int error = WSAGetLastError();
        if (error == WSAECONNRESET || error == WSAECONNABORTED || error == WSAENOTCONN) {
            client_connected_ = false;
            closesocket(client_socket_);
            client_socket_ = INVALID_SOCKET;
            XPLMDebugString("ISFP Connect: Client disconnected\n");
        }
        return false;
    }

    return true;
}

} // namespace ISFP
