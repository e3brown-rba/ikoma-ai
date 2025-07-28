import asyncio
import logging


class DemoRecoveryManager:
    """Handles demo failures and automatic recovery"""

    def __init__(self):
        self._recovery_attempts: dict[str, int] = {}
        self._max_retries = 2
        self._recovery_delays = {
            "timeout": 10,  # Wait 10 seconds before retry
            "connection": 5,  # Wait 5 seconds before retry
            "generic": 3,  # Wait 3 seconds before retry
        }

    async def handle_demo_failure(
        self, agent_id: str, error: str, demo_type: str
    ) -> bool:
        """Handle demo failure with automatic recovery"""
        attempts = self._recovery_attempts.get(agent_id, 0)

        if attempts >= self._max_retries:
            logging.error(f"Demo {agent_id} failed after {attempts} attempts: {error}")
            return False

        self._recovery_attempts[agent_id] = attempts + 1

        # Determine recovery strategy based on error type
        if "timeout" in error.lower():
            return await self._recover_from_timeout(agent_id, demo_type)
        elif "connection" in error.lower() or "network" in error.lower():
            return await self._recover_from_connection_error(agent_id, demo_type)
        else:
            return await self._generic_recovery(agent_id, demo_type)

    async def _recover_from_timeout(self, agent_id: str, demo_type: str) -> bool:
        """Recover from timeout by restarting with longer timeout"""
        logging.info(f"Recovering demo {agent_id} from timeout")

        # Wait before retry
        await asyncio.sleep(self._recovery_delays["timeout"])

        # Return True to indicate recovery should be attempted
        # The actual restart logic will be handled by the calling code
        return True

    async def _recover_from_connection_error(
        self, agent_id: str, demo_type: str
    ) -> bool:
        """Recover from connection errors"""
        logging.info(f"Recovering demo {agent_id} from connection error")

        await asyncio.sleep(self._recovery_delays["connection"])
        return True

    async def _generic_recovery(self, agent_id: str, demo_type: str) -> bool:
        """Generic recovery strategy"""
        logging.info(f"Attempting generic recovery for demo {agent_id}")

        await asyncio.sleep(self._recovery_delays["generic"])
        return True

    def reset_attempts(self, agent_id: str) -> None:
        """Reset recovery attempts for an agent"""
        if agent_id in self._recovery_attempts:
            del self._recovery_attempts[agent_id]

    def get_attempts(self, agent_id: str) -> int:
        """Get number of recovery attempts for an agent"""
        return self._recovery_attempts.get(agent_id, 0)

    def should_retry(self, agent_id: str) -> bool:
        """Check if demo should be retried"""
        return self.get_attempts(agent_id) < self._max_retries


recovery_manager = DemoRecoveryManager()
