// Configuration for API endpoints
import { Platform } from 'react-native';

// Your computer's IP address on the local network
const LOCAL_IP = '192.168.86.26';

export const API_CONFIG = {
  // Use localhost for web/simulator, IP address for physical device
  BASE_URL: Platform.OS === 'web' 
    ? 'http://localhost:8000'
    : `http://${LOCAL_IP}:8000`,
};

// Debug info
console.log('API Base URL:', API_CONFIG.BASE_URL);