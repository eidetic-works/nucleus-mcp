
"""
Nucleus Daemon Manager.
The Kernel service that runs the persistent background agent.

Strategic Role:
- Lifecycle Management: Startup, Shutdown, Signal Handling.
- process Safety: Enforces BrainLock to ensure only one Daemon runs.
- Heartbeat: Updates status for the HUD.
"""

import asyncio
import signal
import sys
import logging
from pathlib import Path
from typing import Optional

from .locking import get_lock, BrainLock
from .policy import DirectivesLoader
from .orchestrator import SwarmsOrchestrator
from .hooks import IdentityKey, AmbientTelemetry, InsightExchange, RemoteExecutionProtocol

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stderr),
        logging.FileHandler("daemon.log")
    ]
)
logger = logging.getLogger("NucleusDaemon")

class DaemonManager:
    def __init__(self, brain_path: Path):
        self.brain_path = brain_path
        self.lock: Optional[BrainLock] = None
        self.running = False
        self.policy_engine = DirectivesLoader(brain_path)
        self.orchestrator = SwarmsOrchestrator(brain_path)
        
        # Strategic Hooks (The Billion Dollar Extensions)
        self.identity = IdentityKey(brain_path)
        self.pulse = AmbientTelemetry(brain_path, identity=self.identity)
        self.insight_exchange = InsightExchange(brain_path)
        self.grid = RemoteExecutionProtocol(brain_path)
        
    async def start(self):
        """Start the Daemon sequence"""
        logger.info("Nucleus Daemon Starting...")
        
        # 1. Acquire Lock
        lock_dir = self.brain_path / ".locks"
        self.lock = get_lock("daemon_process", base_dir=lock_dir)
        
        if not self.lock.acquire(timeout=1.0):
            logger.error("Could not acquire daemon lock. Is another instance running?")
            sys.exit(1)
            
        logger.info("🔒 BrainLock Acquired. I am the Sovereign Process.")
        self.running = True
        
        # 2. Setup Signals
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, lambda: asyncio.create_task(self.shutdown()))
            
        # 3. Load Policy
        policy = self.policy_engine.load_policy()
        logger.info(f"📜 Policy Loaded: Mode={policy.get('mode')}, Safety={policy.get('safety_level')}")
        
        # 4. Main Event Loop
        try:
            await self.main_loop()
        except asyncio.CancelledError:
            logger.info("Daemon cancelled.")
        except Exception as e:
            logger.exception(f"Daemon crashed: {e}")
        finally:
            await self.shutdown()

    async def main_loop(self):
        """The Core Preemptive Loop"""
        logger.info("🚀 Daemon is active. Entering Main Loop.")
        
        while self.running:
            # Heartbeat (The Ambient Pulse)
            status = "busy" if self.orchestrator._active_missions else "idle"
            self.pulse.beat(status, len(self.orchestrator._active_missions))
            logger.debug(f"❤️ Heartbeat ({status})")
            
            # Monitor Swarms
            active_count = len(self.orchestrator._active_missions)
            if active_count > 0:
                logger.info(f"🦾 Active Swarms: {active_count}")
            
            # TODO: Phase A Components
            # - Check AsyncFileWatcher
            # - Check Pending Commitments (SwarmsOrchestrator)
            
            # Simulation of work (Polling interval)
            # In future, this is replaced by Event triggers to avoid busy wait
            await asyncio.sleep(5) 
            
    async def shutdown(self):
        """Graceful Shutdown"""
        if not self.running:
            return
            
        logger.info("🛑 Shutdown initiated...")
        self.running = False
        
        # Release resources
        if self.lock:
            self.lock.release()
            logger.info("🔓 BrainLock Released.")
            
        # TODO: Close sockets, database connections
        
        logger.info("Daemon Stopped.")
        sys.exit(0)

def run_daemon():
    """Entry point for the daemon service"""
    # Determine Brain Path (Environment or Default)
    import os
    brain_path_str = os.environ.get("NUCLEUS_BRAIN_PATH")
    if not brain_path_str:
        # Dev fallback
        brain_path = Path.cwd() / ".brain" # simplistic
    else:
        brain_path = Path(brain_path_str)
        
    daemon = DaemonManager(brain_path)
    try:
        asyncio.run(daemon.start())
    except KeyboardInterrupt:
        pass # Handled in handler
        
if __name__ == "__main__":
    run_daemon()
