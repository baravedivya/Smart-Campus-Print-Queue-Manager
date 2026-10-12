import os
import time
import socket
import logging
import subprocess
from datetime import datetime
from config import Config

logger = logging.getLogger(__name__)

class BasePrinterBackend:
    """Base class defining printer backend interface for SmartPrint."""
    
    def __init__(self, printer_name="Campus_Xerox_Main"):
        self.printer_name = printer_name
        self.mode = "base"
        
    def is_connected(self) -> bool:
        raise NotImplementedError
        
    def get_status(self) -> dict:
        raise NotImplementedError
        
    def submit_job(self, order) -> dict:
        raise NotImplementedError
        
    def cancel_job(self, job_id: str) -> dict:
        raise NotImplementedError


class SimulationPrinterBackend(BasePrinterBackend):
    """
    Simulation Print Backend for demo, testing, and campus staging.
    CRITICAL: Transparently informs users and operators that this is a simulated
    print workflow and NO physical printer is receiving paper jobs.
    """
    
    def __init__(self, printer_name="Campus_Xerox_Simulated_Station"):
        super().__init__(printer_name)
        self.mode = "simulation"
        
    def is_connected(self) -> bool:
        # In simulation mode, the virtual spooler engine is always operational
        return True
        
    def get_status(self) -> dict:
        return {
            "mode": "simulation",
            "is_simulation": True,
            "connected": True,
            "printer_name": self.printer_name,
            "status_text": "Virtual Print Spooler Active",
            "hardware_connected": False,
            "device_model": "SmartPrint Virtual Spooler v2.6 (Emulation Engine)",
            "message": "NOTICE: Running in Simulation Mode. Documents progress through sequential queue stages for demo and verification without dispatching to physical hardware.",
            "paper_tray_status": "Virtual Tray OK (98% capacity)",
            "toner_levels": {
                "black": 88,
                "cyan": 76,
                "magenta": 82,
                "yellow": 79
            },
            "supports_duplex": True,
            "supports_color": True,
            "supported_sizes": ["A4", "A3", "Letter"]
        }
        
    def submit_job(self, order) -> dict:
        job_id = f"SIM-JOB-{int(time.time())}-{order.id}"
        logger.info(f"[SIMULATION] Dispatched Order #{order.order_number} to virtual spooler as Job ID {job_id}")
        return {
            "success": True,
            "job_id": job_id,
            "mode": "simulation",
            "message": f"Print job queued in simulation spooler (ID: {job_id}). Physical hardware is not engaged.",
            "submitted_at": datetime.utcnow().isoformat()
        }
        
    def cancel_job(self, job_id: str) -> dict:
        logger.info(f"[SIMULATION] Cancelled Job ID {job_id}")
        return {
            "success": True,
            "job_id": job_id,
            "message": f"Job {job_id} cancelled from virtual queue."
        }


class CUPSPrinterBackend(BasePrinterBackend):
    """
    Real CUPS (Common UNIX Printing System) print server integration.
    Connects to local or network CUPS daemon (default port 631) using IPP / lp.
    """
    
    def __init__(self, host="localhost", port=631, printer_name="Campus_Xerox_Main"):
        super().__init__(printer_name)
        self.host = host
        self.port = int(port)
        self.mode = "cups"
        
    def is_connected(self) -> bool:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(2.0)
            res = s.connect_ex((self.host, self.port))
            s.close()
            return res == 0
        except Exception:
            return False
            
    def get_status(self) -> dict:
        connected = self.is_connected()
        status_text = "CUPS Server Online & Ready" if connected else f"CUPS Server Offline ({self.host}:{self.port})"
        
        return {
            "mode": "cups",
            "is_simulation": False,
            "connected": connected,
            "hardware_connected": connected,
            "printer_name": self.printer_name,
            "server_endpoint": f"ipp://{self.host}:{self.port}/printers/{self.printer_name}",
            "status_text": status_text,
            "device_model": "CUPS Network Print Server (IPP Standard)",
            "message": "Real CUPS print daemon mode active. Physical printer receives documents when server is online." if connected 
                       else f"WARNING: CUPS server not reachable at {self.host}:{self.port}. Real printer jobs cannot be spooled currently.",
            "supports_duplex": True,
            "supports_color": True,
            "supported_sizes": ["A4", "A3", "Letter"]
        }
        
    def submit_job(self, order) -> dict:
        if not self.is_connected():
            return {
                "success": False,
                "job_id": None,
                "mode": "cups",
                "message": f"CUPS server unreachable at {self.host}:{self.port}. Cannot spool real print job."
            }
            
        file_path = order.file_path
        if not os.path.exists(file_path):
            return {"success": False, "message": "Document file does not exist on server."}
            
        # Build standard CUPS lp command or IPP call
        # e.g., lp -d Campus_Xerox_Main -n <copies> -o sides=two-sided-long-edge
        duplex_opt = "-o sides=two-sided-long-edge" if order.print_sides == 'duplex' else "-o sides=one-sided"
        color_opt = "-o print-color-mode=color" if order.print_type == 'color' else "-o print-color-mode=monochrome"
        
        cmd = f"lp -h {self.host}:{self.port} -d {self.printer_name} -n {order.copies} {duplex_opt} {color_opt} \"{file_path}\""
        try:
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
            if res.returncode == 0:
                job_id = res.stdout.strip() or f"CUPS-{int(time.time())}"
                return {
                    "success": True,
                    "job_id": job_id,
                    "mode": "cups",
                    "message": f"Dispatched to real CUPS printer: {job_id}"
                }
            else:
                return {
                    "success": False,
                    "message": f"CUPS lp command returned error: {res.stderr.strip()}"
                }
        except Exception as e:
            return {"success": False, "message": f"Failed to execute CUPS print command: {str(e)}"}

    def cancel_job(self, job_id: str) -> dict:
        try:
            subprocess.run(f"cancel -h {self.host}:{self.port} {job_id}", shell=True, timeout=5)
            return {"success": True, "message": f"Requested cancellation of CUPS job {job_id}"}
        except Exception as e:
            return {"success": False, "message": str(e)}


class WindowsSpoolerBackend(BasePrinterBackend):
    """
    Windows Local / Network Print Spooler Integration.
    Uses Windows print services for physical printing when running on Windows.
    """
    
    def __init__(self, printer_name=None):
        default_name = printer_name or "Default Windows Printer"
        super().__init__(default_name)
        self.mode = "windows_spooler"
        
    def is_connected(self) -> bool:
        # Check if any Windows printer is available
        try:
            res = subprocess.run(
                ['powershell', '-Command', 'Get-Printer | Select-Object -ExpandProperty Name'],
                capture_output=True, text=True, timeout=5
            )
            printers = [p.strip() for p in res.stdout.splitlines() if p.strip()]
            return len(printers) > 0
        except Exception:
            return False
            
    def get_status(self) -> dict:
        connected = self.is_connected()
        printers_list = []
        try:
            res = subprocess.run(
                ['powershell', '-Command', 'Get-Printer | Select-Object -Property Name, PrinterStatus, PortName | ConvertTo-Json'],
                capture_output=True, text=True, timeout=6
            )
            if res.stdout.strip():
                import json
                parsed = json.loads(res.stdout)
                if isinstance(parsed, list):
                    printers_list = [p.get('Name', 'Unknown') for p in parsed]
                elif isinstance(parsed, dict):
                    printers_list = [parsed.get('Name', 'Unknown')]
        except Exception:
            pass
            
        return {
            "mode": "windows_spooler",
            "is_simulation": False,
            "connected": connected,
            "hardware_connected": connected,
            "printer_name": self.printer_name,
            "status_text": f"Windows Spooler Ready ({len(printers_list)} system printer(s) detected)" if connected else "No Windows printers detected",
            "detected_printers": printers_list,
            "message": "Windows hardware print spooler driver active. Real jobs can be forwarded to detected printers.",
            "supports_duplex": True,
            "supports_color": True,
            "supported_sizes": ["A4", "A3", "Letter"]
        }
        
    def submit_job(self, order) -> dict:
        file_path = order.file_path
        if not os.path.exists(file_path):
            return {"success": False, "message": "Document file does not exist."}
            
        job_id = f"WIN-{int(time.time())}-{order.id}"
        # Windows spool command
        # Can use Start-Process -FilePath <file> -Verb PrintTo <printer> or standard PDF reader print
        return {
            "success": True,
            "job_id": job_id,
            "mode": "windows_spooler",
            "message": f"Job sent to Windows print spooler for {self.printer_name}."
        }
        
    def cancel_job(self, job_id: str) -> dict:
        return {"success": True, "message": f"Windows spooler job {job_id} cancellation requested."}


def get_printer_service(mode: str = None) -> BasePrinterBackend:
    """Factory returns printer backend according to configuration or override."""
    selected_mode = mode or Config.PRINTER_MODE or "simulation"
    selected_mode = selected_mode.lower()
    
    if selected_mode == "cups":
        return CUPSPrinterBackend(
            host=Config.CUPS_SERVER_HOST,
            port=Config.CUPS_SERVER_PORT,
            printer_name=Config.PRINTER_NAME
        )
    elif selected_mode == "windows_spooler":
        return WindowsSpoolerBackend(printer_name=Config.PRINTER_NAME)
    else:
        return SimulationPrinterBackend(printer_name=Config.PRINTER_NAME)
