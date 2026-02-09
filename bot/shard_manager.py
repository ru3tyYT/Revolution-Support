"""
Custom cluster manager for handling 250k+ users.
Manages 5 shards per cluster process for optimal performance.
"""

import asyncio
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .main import SupportBot

logger = logging.getLogger(__name__)


class ShardManager:
    """
    Manages sharding and clustering for large-scale bot deployments.
    
    Discord limits:
    - 2500 guilds per shard (recommended)
    - ~1MB memory per shard
    - 5 shards per cluster process for optimal resource usage
    
    For 250k+ users (approx 1000+ guilds), clustering is essential
    to distribute load across multiple processes.
    """
    
    # Recommended guilds per shard
    GUILDS_PER_SHARD = 2500
    
    def __init__(self, bot: "SupportBot") -> None:
        """Initialize the shard manager."""
        self.bot = bot
        self.from .config import Config
        self.config = Config
        
        self.cluster_id: int | None = self.config.CLUSTER_ID
        self.shards_per_cluster: int = self.config.SHARDS_PER_CLUSTER
        self.total_shards: int | None = self.config.TOTAL_SHARDS
        
        self.shard_ids: list[int] | None = None
        self.is_cluster_mode: bool = False
        
    async def initialize(self) -> None:
        """Initialize the shard manager and calculate shard ranges."""
        logger.info("Initializing ShardManager...")
        
        if not self.config.CLUSTER_ENABLED:
            logger.info("Clustering disabled, using automatic sharding")
            return
        
        if self.cluster_id is None:
            logger.info("No cluster ID set, using automatic sharding")
            return
        
        self.is_cluster_mode = True
        
        # Calculate shard IDs for this cluster
        self.shard_ids = self._calculate_shard_ids()
        
        logger.info(f"Cluster {self.cluster_id}: Managing shards {self.shard_ids}")
        logger.info(f"Shards per cluster: {self.shards_per_cluster}")
        logger.info(f"Total shards: {self.total_shards or 'auto'}")
        
        # Update bot with shard configuration
        await self._configure_bot_shards()
        
    def _calculate_shard_ids(self) -> list[int]:
        """Calculate which shard IDs this cluster should manage."""
        start_shard = self.cluster_id * self.shards_per_cluster
        end_shard = start_shard + self.shards_per_cluster
        
        # Ensure we don't exceed total shards
        if self.total_shards:
            end_shard = min(end_shard, self.total_shards)
        
        shard_range = list(range(start_shard, end_shard))
        
        if not shard_range:
            logger.warning(f"Cluster {self.cluster_id} has no shards assigned!")
        
        return shard_range
    
    async def _configure_bot_shards(self) -> None:
        """Configure the bot with the calculated shard settings."""
        if not self.shard_ids:
            return
        
        # Set shard IDs for this process
        # Note: These attributes need to be set before bot.run() is called
        # This is handled in the setup_hook or by modifying bot initialization
        
        # Calculate total shards if not specified
        if self.total_shards is None:
            # Estimate based on known guild count or use heuristic
            self.total_shards = max(self.shard_ids) + 1
            
            # Ensure we have at least enough shards for this cluster
            min_total = (self.cluster_id + 1) * self.shards_per_cluster
            self.total_shards = max(self.total_shards, min_total)
        
        logger.info(f"Shard configuration: IDs={self.shard_ids}, Total={self.total_shards}")
        
    def get_recommended_shard_count(self, guild_count: int) -> int:
        """
        Calculate recommended number of shards based on guild count.
        
        Args:
            guild_count: Number of guilds the bot is in
            
        Returns:
            Recommended number of shards
        """
        import math
        
        # Base calculation: 1 shard per 2500 guilds
        base_shards = math.ceil(guild_count / self.GUILDS_PER_SHARD)
        
        # Round up to nearest multiple of shards_per_cluster for even distribution
        cluster_count = math.ceil(base_shards / self.shards_per_cluster)
        recommended_shards = cluster_count * self.shards_per_cluster
        
        # Discord recommends at least 1 shard
        return max(1, recommended_shards)
    
    async def get_cluster_status(self) -> dict:
        """
        Get status information for this cluster.
        
        Returns:
            Dictionary with cluster status information
        """
        if not self.is_cluster_mode:
            return {"mode": "single", "shards": "auto"}
        
        guild_count = len(self.bot.guilds)
        member_count = len(set(self.bot.get_all_members()))
        
        shard_status = {}
        if self.bot.shards:
            for shard_id, shard in self.bot.shards.items():
                shard_status[shard_id] = {
                    "latency": shard.latency,
                    "is_ws_ratelimited": shard.is_ws_ratelimited(),
                }
        
        return {
            "mode": "clustered",
            "cluster_id": self.cluster_id,
            "shard_ids": self.shard_ids,
            "total_shards": self.total_shards,
            "guilds": guild_count,
            "members": member_count,
            "shards": shard_status
        }
    
    async def broadcast_to_shards(self, message: dict) -> None:
        """
        Broadcast a message to all shards in this cluster.
        
        Args:
            message: Message dictionary to broadcast
        """
        # This would typically use Redis or another pub/sub system
        # to communicate between clusters
        logger.debug(f"Broadcasting message to shards: {message}")
        
    async def handle_shard_reconnect(self, shard_id: int) -> None:
        """
        Handle shard reconnection events.
        
        Args:
            shard_id: ID of the shard that reconnected
        """
        logger.info(f"Shard {shard_id} reconnected in cluster {self.cluster_id}")
        
        # Notify other clusters via pub/sub if needed
        await self._notify_cluster_event("shard_reconnect", {"shard_id": shard_id})
        
    async def _notify_cluster_event(self, event_type: str, data: dict) -> None:
        """
        Notify other clusters of an event.
        
        Args:
            event_type: Type of event
            data: Event data
        """
        # Placeholder for cluster-to-cluster communication
        # This would typically use Redis pub/sub
        pass
    
    @staticmethod
    def calculate_clusters_needed(total_guilds: int, shards_per_cluster: int = 5) -> tuple[int, int]:
        """
        Calculate how many shards and clusters are needed.
        
        Args:
            total_guilds: Total number of guilds
            shards_per_cluster: Number of shards per cluster
            
        Returns:
            Tuple of (total_shards, total_clusters)
        """
        import math
        
        # Calculate shards needed (1 per 2500 guilds)
        shards_needed = math.ceil(total_guilds / ShardManager.GUILDS_PER_SHARD)
        shards_needed = max(1, shards_needed)
        
        # Calculate clusters needed
        clusters_needed = math.ceil(shards_needed / shards_per_cluster)
        
        return shards_needed, clusters_needed
