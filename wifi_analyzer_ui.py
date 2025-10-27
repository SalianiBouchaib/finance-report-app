"""
Streamlit UI for Enhanced WiFi Network Analyzer
Web interface for the professional-grade network monitoring tool
"""

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import json
import io
import base64
from datetime import datetime
import time

# Import our WiFi analyzer
from wifi_analyzer import WiFiNetworkAnalyzer

def init_wifi_analyzer():
    """Initialize WiFi analyzer in session state"""
    if 'wifi_analyzer' not in st.session_state:
        st.session_state.wifi_analyzer = WiFiNetworkAnalyzer()
    return st.session_state.wifi_analyzer

def show_wifi_analyzer_page():
    """Main WiFi analyzer page"""
    st.title("🌐 Enhanced WiFi Network Analyzer")
    st.markdown("Professional-grade network monitoring with accurate distance calculation and real-time analysis")
    
    # Initialize analyzer
    analyzer = init_wifi_analyzer()
    
    # Sidebar controls
    with st.sidebar:
        st.header("⚙️ Control Panel")
        
        # Scan settings
        st.subheader("Scan Settings")
        network_range = st.text_input("Network Range", value="192.168.1.0/24")
        scan_interval = st.slider("Monitoring Interval (seconds)", 10, 300, 30)
        
        # Actions
        st.subheader("Actions")
        if st.button("🔍 Quick Scan", type="primary"):
            with st.spinner("Scanning network..."):
                perform_network_scan(analyzer)
        
        if st.button("📊 Generate Report"):
            with st.spinner("Generating report..."):
                generate_network_report(analyzer)
        
        # Real-time monitoring
        st.subheader("Real-time Monitoring")
        if 'monitoring_active' not in st.session_state:
            st.session_state.monitoring_active = False
        
        if st.button("▶️ Start Monitoring" if not st.session_state.monitoring_active else "⏹️ Stop Monitoring"):
            toggle_monitoring(analyzer, scan_interval)
        
        if st.session_state.monitoring_active:
            st.success("🟢 Monitoring Active")
        else:
            st.info("🔴 Monitoring Inactive")
    
    # Main content area
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Dashboard", "🗺️ Network Map", "📱 Devices", "🔒 Security", "📈 History"])
    
    with tab1:
        show_dashboard_tab(analyzer)
    
    with tab2:
        show_network_map_tab(analyzer)
    
    with tab3:
        show_devices_tab(analyzer)
    
    with tab4:
        show_security_tab(analyzer)
    
    with tab5:
        show_history_tab(analyzer)

def perform_network_scan(analyzer):
    """Perform a network scan and update session state"""
    try:
        # Get WiFi profiles
        profiles = analyzer.get_wifi_profiles()
        
        # Discover devices
        devices = analyzer.discover_devices_nmap()
        upnp_devices = analyzer.discover_devices_upnp()
        
        # Calculate distances
        for profile in profiles:
            distance = analyzer.calculate_rssi_distance(profile['rssi'], profile['frequency'])
            profile['distance'] = distance
        
        # Calculate positions
        positions = analyzer.calculate_device_positions(devices, profiles)
        
        # Store in session state
        st.session_state.last_scan = {
            'timestamp': datetime.now(),
            'profiles': profiles,
            'devices': devices,
            'upnp_devices': upnp_devices,
            'positions': positions
        }
        
        st.success(f"✅ Scan completed! Found {len(profiles)} access points and {len(devices) + len(upnp_devices)} devices")
        
    except Exception as e:
        st.error(f"❌ Scan failed: {str(e)}")

def generate_network_report(analyzer):
    """Generate and display network report"""
    try:
        report = analyzer.generate_network_report()
        st.session_state.network_report = report
        st.success("✅ Network report generated successfully!")
        
    except Exception as e:
        st.error(f"❌ Report generation failed: {str(e)}")

def toggle_monitoring(analyzer, interval):
    """Toggle real-time monitoring"""
    if st.session_state.monitoring_active:
        analyzer.stop_real_time_monitoring()
        st.session_state.monitoring_active = False
        st.success("Monitoring stopped")
    else:
        analyzer.start_real_time_monitoring(interval)
        st.session_state.monitoring_active = True
        st.success(f"Monitoring started (interval: {interval}s)")

def show_dashboard_tab(analyzer):
    """Show main dashboard with key metrics"""
    st.header("📊 Network Dashboard")
    
    # Check if we have recent data
    if 'network_report' not in st.session_state:
        st.info("👆 Click 'Generate Report' in the sidebar to see network analysis")
        return
    
    report = st.session_state.network_report
    summary = report['summary']
    
    # Key metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Access Points",
            summary['total_access_points'],
            help="Number of WiFi access points detected"
        )
    
    with col2:
        st.metric(
            "Connected Devices",
            summary['total_devices'],
            help="Total devices discovered on the network"
        )
    
    with col3:
        st.metric(
            "Avg Signal Strength",
            f"{summary['average_signal_strength']:.1f} dBm",
            help="Average RSSI across all access points"
        )
    
    with col4:
        st.metric(
            "Coverage Area",
            f"{summary['network_coverage_area']:.0f} m²",
            help="Estimated network coverage area"
        )
    
    # Security overview
    st.subheader("🔒 Security Overview")
    security = report['security_analysis']
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Security score gauge
        score = security['security_score']
        if score >= 80:
            color = "green"
            status = "Excellent"
        elif score >= 60:
            color = "orange"
            status = "Good"
        else:
            color = "red"
            status = "Needs Improvement"
        
        st.metric(
            "Security Score",
            f"{score:.1f}/100",
            delta=status
        )
    
    with col2:
        # Security breakdown
        security_data = {
            'Open Networks': security['open_networks'],
            'WEP Networks': security['wep_networks'],
            'WPA Networks': security['wpa_networks'],
            'WPA2 Networks': security['wpa2_networks'],
            'WPA3 Networks': security['wpa3_networks']
        }
        
        # Filter out zero values
        security_data = {k: v for k, v in security_data.items() if v > 0}
        
        if security_data:
            fig, ax = plt.subplots(figsize=(6, 4))
            colors = ['red', 'orange', 'yellow', 'lightgreen', 'green'][:len(security_data)]
            ax.pie(security_data.values(), labels=security_data.keys(), 
                   autopct='%1.0f', colors=colors, startangle=90)
            ax.set_title("Network Security Distribution")
            st.pyplot(fig)
            plt.close()
    
    # Recommendations
    st.subheader("💡 Recommendations")
    for rec in report['recommendations']:
        st.info(f"• {rec}")
    
    # Export options
    st.subheader("📤 Export Options")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📊 Export JSON Report"):
            json_str = json.dumps(report, indent=2, default=str)
            st.download_button(
                label="Download JSON",
                data=json_str,
                file_name=f"network_report_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
                mime="application/json"
            )
    
    with col2:
        if st.button("🗺️ Export KML"):
            try:
                kml_path = "network_analysis.kml"
                analyzer.export_to_kml(report['devices'], report['device_positions'], kml_path)
                with open(kml_path, 'r') as f:
                    kml_content = f.read()
                st.download_button(
                    label="Download KML",
                    data=kml_content,
                    file_name=f"network_analysis_{datetime.now().strftime('%Y%m%d_%H%M')}.kml",
                    mime="application/vnd.google-earth.kml+xml"
                )
            except Exception as e:
                st.error(f"KML export failed: {e}")
    
    with col3:
        if st.button("📋 Export CSV"):
            try:
                # Create devices DataFrame
                devices_df = pd.DataFrame(report['devices'])
                csv_buffer = io.StringIO()
                devices_df.to_csv(csv_buffer, index=False)
                st.download_button(
                    label="Download CSV",
                    data=csv_buffer.getvalue(),
                    file_name=f"network_devices_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                    mime="text/csv"
                )
            except Exception as e:
                st.error(f"CSV export failed: {e}")

def show_network_map_tab(analyzer):
    """Show interactive network map"""
    st.header("🗺️ Network Topology Map")
    
    if 'network_report' not in st.session_state:
        st.info("👆 Generate a report first to see the network map")
        return
    
    report = st.session_state.network_report
    
    try:
        # Create visualization
        fig = analyzer.create_network_visualization(
            report['devices'], 
            report['access_points'], 
            report['device_positions']
        )
        
        st.pyplot(fig)
        plt.close()
        
        # Map controls
        st.subheader("🎛️ Map Controls")
        col1, col2 = st.columns(2)
        
        with col1:
            show_signal_contours = st.checkbox("Show Signal Contours", value=True)
            show_device_labels = st.checkbox("Show Device Labels", value=True)
        
        with col2:
            show_connection_lines = st.checkbox("Show Connection Lines", value=True)
            show_coverage_areas = st.checkbox("Show Coverage Areas", value=True)
        
        # 3D visualization option
        if st.button("🎯 Generate 3D Visualization"):
            try:
                create_3d_visualization(report)
            except Exception as e:
                st.error(f"3D visualization failed: {e}")
        
    except Exception as e:
        st.error(f"Map generation failed: {e}")

def create_3d_visualization(report):
    """Create 3D network visualization"""
    from mpl_toolkits.mplot3d import Axes3D
    
    fig = plt.figure(figsize=(12, 8))
    ax = fig.add_subplot(111, projection='3d')
    
    # Plot access points
    for i, ap in enumerate(report['access_points']):
        if i == 0:
            x, y, z = 20, 50, 10
        elif i == 1:
            x, y, z = 80, 50, 10
        else:
            x, y, z = 50, 20 + (i-2) * 30, 10
        
        ax.scatter(x, y, z, c='red', s=100, marker='^', label='Access Points' if i == 0 else "")
    
    # Plot devices
    for device_id, (x, y, distance) in report['device_positions'].items():
        z = max(1, 10 - distance/5)  # Height based on signal strength
        ax.scatter(x, y, z, c='blue', s=50, marker='o', alpha=0.7)
    
    ax.set_xlabel('X (meters)')
    ax.set_ylabel('Y (meters)')
    ax.set_zlabel('Signal Strength')
    ax.set_title('3D Network Topology')
    ax.legend()
    
    st.pyplot(fig)
    plt.close()

def show_devices_tab(analyzer):
    """Show detailed device information"""
    st.header("📱 Device Discovery & Analysis")
    
    if 'network_report' not in st.session_state:
        st.info("👆 Generate a report first to see device details")
        return
    
    report = st.session_state.network_report
    
    # Device summary
    st.subheader("📊 Device Summary")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Devices", len(report['devices']) + len(report['upnp_devices']))
    with col2:
        unique_vendors = len(set(d.get('vendor', 'Unknown') for d in report['devices']))
        st.metric("Unique Vendors", unique_vendors)
    with col3:
        active_devices = len([d for d in report['devices'] if d.get('ip')])
        st.metric("Active Devices", active_devices)
    
    # Device tables
    st.subheader("🔍 Discovered Devices")
    
    if report['devices']:
        # Regular devices
        devices_df = pd.DataFrame(report['devices'])
        
        # Add distance information if available
        for idx, device in devices_df.iterrows():
            mac = device.get('mac', 'Unknown')
            if mac in report['device_positions']:
                x, y, distance = report['device_positions'][mac]
                devices_df.at[idx, 'estimated_distance'] = f"{distance:.1f}m"
        
        st.dataframe(
            devices_df,
            use_container_width=True,
            column_config={
                "ip": "IP Address",
                "hostname": "Hostname",
                "mac": "MAC Address",
                "vendor": "Vendor",
                "estimated_distance": "Distance",
                "discovery_method": "Discovery Method"
            }
        )
    else:
        st.info("No devices discovered. Try running a network scan.")
    
    # UPnP devices
    if report['upnp_devices']:
        st.subheader("🌐 UPnP Devices")
        upnp_df = pd.DataFrame(report['upnp_devices'])
        st.dataframe(upnp_df, use_container_width=True)
    
    # Device type analysis
    if report['devices']:
        st.subheader("📈 Device Analysis")
        
        # Vendor distribution
        vendor_counts = {}
        for device in report['devices']:
            vendor = device.get('vendor', 'Unknown')
            vendor_counts[vendor] = vendor_counts.get(vendor, 0) + 1
        
        if vendor_counts:
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**Vendor Distribution**")
                vendor_df = pd.DataFrame(list(vendor_counts.items()), columns=['Vendor', 'Count'])
                st.dataframe(vendor_df)
            
            with col2:
                fig, ax = plt.subplots(figsize=(8, 6))
                ax.bar(vendor_counts.keys(), vendor_counts.values())
                ax.set_title('Devices by Vendor')
                ax.set_xlabel('Vendor')
                ax.set_ylabel('Device Count')
                plt.xticks(rotation=45, ha='right')
                plt.tight_layout()
                st.pyplot(fig)
                plt.close()

def show_security_tab(analyzer):
    """Show security analysis"""
    st.header("🔒 Network Security Analysis")
    
    if 'network_report' not in st.session_state:
        st.info("👆 Generate a report first to see security analysis")
        return
    
    report = st.session_state.network_report
    security = report['security_analysis']
    
    # Security score display
    st.subheader("🛡️ Security Score")
    score = security['security_score']
    
    # Create a progress bar for security score
    progress_color = "green" if score >= 80 else "orange" if score >= 60 else "red"
    st.metric("Overall Security Score", f"{score:.1f}/100")
    st.progress(score / 100)
    
    # Security breakdown
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🔐 Encryption Analysis")
        security_data = {
            'Open Networks': security['open_networks'],
            'WEP (Weak)': security['wep_networks'],
            'WPA (Legacy)': security['wpa_networks'],
            'WPA2 (Good)': security['wpa2_networks'],
            'WPA3 (Best)': security['wpa3_networks']
        }
        
        for sec_type, count in security_data.items():
            if count > 0:
                if 'Open' in sec_type or 'WEP' in sec_type:
                    st.error(f"⚠️ {sec_type}: {count} network(s)")
                elif 'WPA3' in sec_type:
                    st.success(f"✅ {sec_type}: {count} network(s)")
                else:
                    st.info(f"ℹ️ {sec_type}: {count} network(s)")
    
    with col2:
        st.subheader("📊 Security Distribution")
        # Filter out zero values for pie chart
        chart_data = {k: v for k, v in security_data.items() if v > 0}
        
        if chart_data:
            fig, ax = plt.subplots(figsize=(6, 6))
            colors = ['red', 'orange', 'yellow', 'lightgreen', 'green'][:len(chart_data)]
            wedges, texts, autotexts = ax.pie(
                chart_data.values(), 
                labels=chart_data.keys(),
                autopct='%1.0f%%',
                colors=colors,
                startangle=90
            )
            ax.set_title("Network Security Types")
            st.pyplot(fig)
            plt.close()
    
    # Security recommendations
    st.subheader("💡 Security Recommendations")
    
    if security['open_networks'] > 0:
        st.error(f"🚨 **Critical**: {security['open_networks']} open network(s) detected! Enable WPA2/WPA3 encryption immediately.")
    
    if security['wep_networks'] > 0:
        st.warning(f"⚠️ **High Risk**: {security['wep_networks']} WEP-encrypted network(s) found. Upgrade to WPA2/WPA3.")
    
    if security['wpa_networks'] > 0:
        st.warning(f"⚠️ **Medium Risk**: {security['wpa_networks']} legacy WPA network(s). Consider upgrading to WPA2/WPA3.")
    
    if security['wpa3_networks'] > 0:
        st.success(f"✅ **Excellent**: {security['wpa3_networks']} WPA3-secured network(s) detected.")
    
    # Access point details
    st.subheader("📡 Access Point Security Details")
    if report['access_points']:
        ap_df = pd.DataFrame(report['access_points'])
        ap_security_df = ap_df[['ssid', 'security', 'rssi', 'frequency']].copy()
        
        # Add security rating
        def get_security_rating(security):
            security_lower = str(security).lower()
            if 'wpa3' in security_lower:
                return "🟢 Excellent"
            elif 'wpa2' in security_lower:
                return "🟡 Good"
            elif 'wpa' in security_lower:
                return "🟠 Fair"
            elif 'wep' in security_lower:
                return "🔴 Poor"
            else:
                return "🔴 Critical"
        
        ap_security_df['Security Rating'] = ap_df['security'].apply(get_security_rating)
        
        st.dataframe(
            ap_security_df,
            use_container_width=True,
            column_config={
                "ssid": "Network Name",
                "security": "Encryption",
                "rssi": "Signal (dBm)",
                "frequency": "Frequency (GHz)",
                "Security Rating": "Security Level"
            }
        )

def show_history_tab(analyzer):
    """Show monitoring history and trends"""
    st.header("📈 Monitoring History & Trends")
    
    # Check if monitoring has been active
    if not hasattr(analyzer, 'history') or not analyzer.history:
        st.info("📊 No monitoring history available. Start real-time monitoring to see trends over time.")
        return
    
    # Display history summary
    st.subheader("📊 History Summary")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("History Records", len(analyzer.history))
    with col2:
        if analyzer.history:
            latest = analyzer.history[-1]['timestamp']
            st.metric("Last Update", latest.strftime("%H:%M:%S"))
    with col3:
        monitoring_status = "🟢 Active" if st.session_state.get('monitoring_active', False) else "🔴 Inactive"
        st.metric("Monitoring", monitoring_status)
    
    # Plot trends
    if len(analyzer.history) > 1:
        st.subheader("📈 Signal Strength Trends")
        
        # Prepare data for plotting
        timestamps = []
        avg_signals = []
        device_counts = []
        
        for record in analyzer.history:
            timestamps.append(record['timestamp'])
            
            # Calculate average signal strength
            aps = record.get('access_points', [])
            if aps:
                avg_signal = np.mean([ap.get('rssi', -90) for ap in aps])
                avg_signals.append(avg_signal)
            else:
                avg_signals.append(-90)
            
            # Count devices
            device_counts.append(len(record.get('devices', [])))
        
        # Create plots
        col1, col2 = st.columns(2)
        
        with col1:
            # Signal strength trend
            fig, ax = plt.subplots(figsize=(8, 4))
            ax.plot(timestamps, avg_signals, 'b-', marker='o')
            ax.set_title('Average Signal Strength Over Time')
            ax.set_xlabel('Time')
            ax.set_ylabel('RSSI (dBm)')
            ax.grid(True, alpha=0.3)
            plt.xticks(rotation=45)
            plt.tight_layout()
            st.pyplot(fig)
            plt.close()
        
        with col2:
            # Device count trend
            fig, ax = plt.subplots(figsize=(8, 4))
            ax.plot(timestamps, device_counts, 'g-', marker='s')
            ax.set_title('Device Count Over Time')
            ax.set_xlabel('Time')
            ax.set_ylabel('Number of Devices')
            ax.grid(True, alpha=0.3)
            plt.xticks(rotation=45)
            plt.tight_layout()
            st.pyplot(fig)
            plt.close()
        
        # History table
        st.subheader("📋 Recent History")
        history_data = []
        for record in analyzer.history[-10:]:  # Show last 10 records
            history_data.append({
                'Timestamp': record['timestamp'].strftime("%Y-%m-%d %H:%M:%S"),
                'Access Points': len(record.get('access_points', [])),
                'Devices': len(record.get('devices', [])),
                'Avg Signal': f"{np.mean([ap.get('rssi', -90) for ap in record.get('access_points', [])]) if record.get('access_points') else -90:.1f} dBm"
            })
        
        if history_data:
            history_df = pd.DataFrame(history_data)
            st.dataframe(history_df, use_container_width=True)
    
    # Clear history option
    if st.button("🗑️ Clear History"):
        analyzer.history.clear()
        st.success("History cleared")
        st.rerun()


def main():
    """Main function for WiFi analyzer UI"""
    st.set_page_config(
        page_title="WiFi Network Analyzer",
        page_icon="🌐",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    show_wifi_analyzer_page()


if __name__ == "__main__":
    main()