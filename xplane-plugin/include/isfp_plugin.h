#ifndef ISFP_PLUGIN_H
#define ISFP_PLUGIN_H

// Prevent Windows Socket API conflicts
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif

#ifndef _WINSOCKAPI_
#define _WINSOCKAPI_
#endif

#include <windows.h>
#include <winsock2.h>
#include <ws2tcpip.h>
#include <string>
#include <thread>
#include <atomic>
#include <mutex>
#include <queue>

// X-Plane SDK Headers
#include "XPLMPlugin.h"
#include "XPLMUtilities.h"
#include "XPLMDataAccess.h"
#include "XPLMProcessing.h"

#pragma comment(lib, "ws2_32.lib")

namespace ISFP {

// Plugin version info
constexpr const char* PLUGIN_NAME = "ISFP Connect";
constexpr const char* PLUGIN_SIGNATURE = "com.isfp.connect";
constexpr const char* PLUGIN_DESCRIPTION = "ISFP Connect Plugin for X-Plane - Native TCP Server";
constexpr int PLUGIN_VERSION = 100;

// Default server config - plugin acts as server
constexpr const char* DEFAULT_HOST = "0.0.0.0";  // Listen on all interfaces
constexpr int DEFAULT_PORT = 51001;
constexpr int DATA_SEND_INTERVAL_MS = 500; // 2Hz data send frequency

// Flight data structure
struct FlightData {
    double latitude;
    double longitude;
    double altitude;
    double elevation;
    double pitch;
    double roll;
    double heading;
    double indicated_airspeed;
    double true_airspeed;
    double groundspeed;
    double vertical_speed;
    double altitude_msl;
    double altitude_agl;
    double mag_heading;
    double true_heading;
    int com1_freq;
    int com2_freq;
    int transponder;
    int gear_deploy;
    float flaps_ratio;
    float throttle_ratio;
    bool valid;
    
    FlightData() : valid(false) {}
};

// Network manager class - acts as TCP server
class NetworkManager {
public:
    NetworkManager();
    ~NetworkManager();
    
    bool Initialize();
    void Shutdown();
    
    bool StartServer(int port);  // Start listening
    void StopServer();
    bool IsClientConnected() const { return client_connected_; }
    
    bool SendData(const FlightData& data);
    
private:
    void ServerLoop();  // Accept connections
    void ClientLoop();  // Handle client communication
    
    SOCKET listen_socket_;
    SOCKET client_socket_;
    std::atomic<bool> server_running_;
    std::atomic<bool> client_connected_;
    
    int port_;
    
    std::thread server_thread_;
    std::mutex socket_mutex_;
    
    WSADATA wsa_data_;
    bool wsa_initialized_;
};

// DataRef manager class
class DataRefManager {
public:
    DataRefManager();
    ~DataRefManager();
    
    bool Initialize();
    void Shutdown();
    
    FlightData GetFlightData();
    
    void SetCom1Freq(int freq);
    void SetCom2Freq(int freq);
    void SetTransponder(int code);
    
private:
    void FindDataRefs();
    
    XPLMDataRef dr_latitude_;
    XPLMDataRef dr_longitude_;
    XPLMDataRef dr_altitude_;
    XPLMDataRef dr_elevation_;
    XPLMDataRef dr_pitch_;
    XPLMDataRef dr_roll_;
    XPLMDataRef dr_heading_;
    XPLMDataRef dr_indicated_airspeed_;
    XPLMDataRef dr_true_airspeed_;
    XPLMDataRef dr_groundspeed_;
    XPLMDataRef dr_vertical_speed_;
    XPLMDataRef dr_altitude_msl_;
    XPLMDataRef dr_altitude_agl_;
    XPLMDataRef dr_mag_heading_;
    XPLMDataRef dr_true_heading_;
    XPLMDataRef dr_com1_freq_;
    XPLMDataRef dr_com2_freq_;
    XPLMDataRef dr_transponder_;
    XPLMDataRef dr_gear_deploy_;
    XPLMDataRef dr_flaps_ratio_;
    XPLMDataRef dr_throttle_ratio_;
};

// Global instances
extern NetworkManager* g_network;
extern DataRefManager* g_datarefs;

} // namespace ISFP

#endif // ISFP_PLUGIN_H
