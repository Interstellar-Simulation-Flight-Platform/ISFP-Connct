/*
 * ISFP Connect - DataRef Manager
 * Manages X-Plane DataRefs reading and writing
 */

#include "isfp_plugin.h"
#include <cmath>

namespace ISFP {

DataRefManager::DataRefManager() {
    // Initialize all DataRefs to nullptr
    dr_latitude_ = nullptr;
    dr_longitude_ = nullptr;
    dr_altitude_ = nullptr;
    dr_elevation_ = nullptr;
    dr_pitch_ = nullptr;
    dr_roll_ = nullptr;
    dr_heading_ = nullptr;
    dr_indicated_airspeed_ = nullptr;
    dr_true_airspeed_ = nullptr;
    dr_groundspeed_ = nullptr;
    dr_vertical_speed_ = nullptr;
    dr_altitude_msl_ = nullptr;
    dr_altitude_agl_ = nullptr;
    dr_mag_heading_ = nullptr;
    dr_true_heading_ = nullptr;
    dr_com1_freq_ = nullptr;
    dr_com2_freq_ = nullptr;
    dr_transponder_ = nullptr;
    dr_gear_deploy_ = nullptr;
    dr_flaps_ratio_ = nullptr;
    dr_throttle_ratio_ = nullptr;
}

DataRefManager::~DataRefManager() {
    Shutdown();
}

bool DataRefManager::Initialize() {
    FindDataRefs();
    XPLMDebugString("ISFP Connect: DataRef manager initialized\n");
    return true;
}

void DataRefManager::Shutdown() {
    XPLMDebugString("ISFP Connect: DataRef manager shutdown\n");
}

void DataRefManager::FindDataRefs() {
    // Position data
    dr_latitude_ = XPLMFindDataRef("sim/flightmodel/position/latitude");
    dr_longitude_ = XPLMFindDataRef("sim/flightmodel/position/longitude");
    dr_altitude_ = XPLMFindDataRef("sim/flightmodel/position/elevation");
    dr_elevation_ = XPLMFindDataRef("sim/flightmodel/position/y_agl");
    
    // Attitude data
    dr_pitch_ = XPLMFindDataRef("sim/flightmodel/position/theta");
    dr_roll_ = XPLMFindDataRef("sim/flightmodel/position/phi");
    dr_heading_ = XPLMFindDataRef("sim/flightmodel/position/psi");
    
    // Speed data
    dr_indicated_airspeed_ = XPLMFindDataRef("sim/flightmodel/position/indicated_airspeed");
    dr_true_airspeed_ = XPLMFindDataRef("sim/flightmodel/position/true_airspeed");
    dr_groundspeed_ = XPLMFindDataRef("sim/flightmodel/position/groundspeed");
    dr_vertical_speed_ = XPLMFindDataRef("sim/flightmodel/position/vh_ind");
    
    // Altitude data
    dr_altitude_msl_ = XPLMFindDataRef("sim/flightmodel/position/elevation");
    dr_altitude_agl_ = XPLMFindDataRef("sim/flightmodel/position/y_agl");
    
    // Heading data
    dr_mag_heading_ = XPLMFindDataRef("sim/flightmodel/position/magpsi");
    dr_true_heading_ = XPLMFindDataRef("sim/flightmodel/position/true_psi");
    
    // Radio data
    dr_com1_freq_ = XPLMFindDataRef("sim/cockpit/radios/com1_freq_hz");
    dr_com2_freq_ = XPLMFindDataRef("sim/cockpit/radios/com2_freq_hz");
    dr_transponder_ = XPLMFindDataRef("sim/cockpit/radios/transponder_code");
    
    // Landing gear
    dr_gear_deploy_ = XPLMFindDataRef("sim/aircraft/parts/acf_gear_deploy");
    
    // Flaps
    dr_flaps_ratio_ = XPLMFindDataRef("sim/flightmodel/controls/flaprat");
    
    // Throttle
    dr_throttle_ratio_ = XPLMFindDataRef("sim/cockpit2/engine/actuators/throttle_ratio_all");
}

FlightData DataRefManager::GetFlightData() {
    FlightData data;
    
    // Check if critical DataRefs are valid
    if (!dr_latitude_ || !dr_longitude_) {
        data.valid = false;
        return data;
    }
    
    // Read position
    data.latitude = XPLMGetDatad(dr_latitude_);
    data.longitude = XPLMGetDatad(dr_longitude_);
    data.altitude = dr_altitude_ ? XPLMGetDatad(dr_altitude_) : 0.0;
    data.elevation = dr_elevation_ ? XPLMGetDatad(dr_elevation_) : 0.0;
    
    // Read attitude (convert to radians)
    data.pitch = dr_pitch_ ? XPLMGetDataf(dr_pitch_) * 3.14159f / 180.0f : 0.0f;
    data.roll = dr_roll_ ? XPLMGetDataf(dr_roll_) * 3.14159f / 180.0f : 0.0f;
    data.heading = dr_heading_ ? XPLMGetDataf(dr_heading_) : 0.0f;
    
    // Read speed
    data.indicated_airspeed = dr_indicated_airspeed_ ? XPLMGetDataf(dr_indicated_airspeed_) : 0.0f;
    data.true_airspeed = dr_true_airspeed_ ? XPLMGetDataf(dr_true_airspeed_) : 0.0f;
    data.groundspeed = dr_groundspeed_ ? XPLMGetDataf(dr_groundspeed_) * 1.94384f : 0.0f;
    data.vertical_speed = dr_vertical_speed_ ? XPLMGetDataf(dr_vertical_speed_) : 0.0f;
    
    // Read altitude
    data.altitude_msl = dr_altitude_msl_ ? XPLMGetDatad(dr_altitude_msl_) * 3.28084 : 0.0;
    data.altitude_agl = dr_altitude_agl_ ? XPLMGetDatad(dr_altitude_agl_) * 3.28084 : 0.0;
    
    // Read heading
    data.mag_heading = dr_mag_heading_ ? XPLMGetDataf(dr_mag_heading_) : 0.0f;
    data.true_heading = dr_true_heading_ ? XPLMGetDataf(dr_true_heading_) : 0.0f;
    
    // Read radio frequencies
    data.com1_freq = dr_com1_freq_ ? XPLMGetDatai(dr_com1_freq_) : 0;
    data.com2_freq = dr_com2_freq_ ? XPLMGetDatai(dr_com2_freq_) : 0;
    data.transponder = dr_transponder_ ? XPLMGetDatai(dr_transponder_) : 0;
    
    // Read landing gear status
    if (dr_gear_deploy_) {
        float gear[10];
        XPLMGetDatavf(dr_gear_deploy_, gear, 0, 10);
        data.gear_deploy = (gear[0] > 0.5f) ? 1 : 0;
    } else {
        data.gear_deploy = 0;
    }
    
    // Read flaps position
    data.flaps_ratio = dr_flaps_ratio_ ? XPLMGetDataf(dr_flaps_ratio_) : 0.0f;
    
    // Read throttle position
    data.throttle_ratio = dr_throttle_ratio_ ? XPLMGetDataf(dr_throttle_ratio_) : 0.0f;
    
    data.valid = true;
    return data;
}

void DataRefManager::SetCom1Freq(int freq) {
    if (dr_com1_freq_ && XPLMCanWriteDataRef(dr_com1_freq_)) {
        XPLMSetDatai(dr_com1_freq_, freq);
    }
}

void DataRefManager::SetCom2Freq(int freq) {
    if (dr_com2_freq_ && XPLMCanWriteDataRef(dr_com2_freq_)) {
        XPLMSetDatai(dr_com2_freq_, freq);
    }
}

void DataRefManager::SetTransponder(int code) {
    if (dr_transponder_ && XPLMCanWriteDataRef(dr_transponder_)) {
        XPLMSetDatai(dr_transponder_, code);
    }
}

} // namespace ISFP
