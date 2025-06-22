"""
Ngrok tunnel manager for local development and testing
"""
import os
import logging
import time
from typing import Optional, Dict, Any
from pyngrok import ngrok, conf
from pyngrok.exception import PyngrokNgrokError

logger = logging.getLogger(__name__)

class NgrokManager:
    """Manages ngrok tunnels for local development"""
    
    def __init__(self):
        self.tunnel = None
        self.public_url = None
        self._configured = False
    
    def configure_ngrok(self, auth_token: str = None) -> bool:
        """Configure ngrok with auth token if provided"""
        try:
            if auth_token:
                ngrok.set_auth_token(auth_token)
                logger.info("Ngrok auth token configured")
            
            # Set ngrok config path for Windows
            if os.name == 'nt':  # Windows
                ngrok_config_path = os.path.expanduser("~/.ngrok2/ngrok.yml")
                if not os.path.exists(os.path.dirname(ngrok_config_path)):
                    os.makedirs(os.path.dirname(ngrok_config_path), exist_ok=True)
            
            self._configured = True
            return True
            
        except Exception as e:
            logger.error(f"Failed to configure ngrok: {e}")
            return False
    
    def start_tunnel(self, port: int = 8000, protocol: str = "http") -> Optional[str]:
        """Start ngrok tunnel and return public URL"""
        try:
            if not self._configured:
                self.configure_ngrok()
            
            # Kill any existing tunnels
            self.stop_tunnel()
            
            logger.info(f"Starting ngrok tunnel for port {port}...")
            
            # Create tunnel
            self.tunnel = ngrok.connect(port, protocol)
            self.public_url = self.tunnel.public_url
            
            # Ensure HTTPS URL
            if self.public_url.startswith("http://"):
                self.public_url = self.public_url.replace("http://", "https://")
            
            logger.info(f"Ngrok tunnel started: {self.public_url}")
            
            # Wait a moment for tunnel to be ready
            time.sleep(2)
            
            return self.public_url
            
        except PyngrokNgrokError as e:
            logger.error(f"Ngrok error: {e}")
            if "ngrok executable not found" in str(e).lower():
                logger.error("Please install ngrok: https://ngrok.com/download")
            elif "authentication required" in str(e).lower():
                logger.error("Please configure ngrok auth token: ngrok authtoken YOUR_TOKEN")
            return None
            
        except Exception as e:
            logger.error(f"Unexpected error starting ngrok tunnel: {e}")
            return None
    
    def stop_tunnel(self):
        """Stop the current ngrok tunnel"""
        try:
            if self.tunnel:
                ngrok.disconnect(self.tunnel.public_url)
                logger.info(f"Stopped ngrok tunnel: {self.tunnel.public_url}")
                self.tunnel = None
                self.public_url = None
        except Exception as e:
            logger.warning(f"Error stopping ngrok tunnel: {e}")
    
    def get_tunnels_info(self) -> Dict[str, Any]:
        """Get information about active tunnels"""
        try:
            tunnels = ngrok.get_tunnels()
            return {
                "active_tunnels": len(tunnels),
                "tunnels": [
                    {
                        "name": tunnel.name,
                        "public_url": tunnel.public_url,
                        "proto": tunnel.proto,
                        "config": tunnel.config
                    }
                    for tunnel in tunnels
                ]
            }
        except Exception as e:
            logger.error(f"Error getting tunnels info: {e}")
            return {"active_tunnels": 0, "tunnels": []}
    
    def is_tunnel_active(self) -> bool:
        """Check if tunnel is active and accessible"""
        if not self.public_url:
            return False
        
        try:
            import requests
            response = requests.get(f"{self.public_url}/api/health", timeout=10)
            return response.status_code == 200
        except Exception:
            return False
    
    def wait_for_tunnel(self, timeout: int = 30) -> bool:
        """Wait for tunnel to become active"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.is_tunnel_active():
                logger.info("Ngrok tunnel is active and accessible")
                return True
            time.sleep(2)
        
        logger.warning("Ngrok tunnel did not become accessible within timeout")
        return False
    
    def cleanup(self):
        """Cleanup all ngrok resources"""
        try:
            ngrok.kill()
            logger.info("Ngrok process killed")
        except Exception as e:
            logger.warning(f"Error during ngrok cleanup: {e}")

# Global instance
ngrok_manager = NgrokManager()

def get_ngrok_url() -> Optional[str]:
    """Get current ngrok public URL"""
    return ngrok_manager.public_url

def start_ngrok_tunnel(port: int = 8000, auth_token: str = None) -> Optional[str]:
    """Start ngrok tunnel with optional auth token"""
    if auth_token:
        ngrok_manager.configure_ngrok(auth_token)
    
    return ngrok_manager.start_tunnel(port)

def stop_ngrok_tunnel():
    """Stop ngrok tunnel"""
    ngrok_manager.stop_tunnel()

def cleanup_ngrok():
    """Cleanup ngrok resources"""
    ngrok_manager.cleanup() 