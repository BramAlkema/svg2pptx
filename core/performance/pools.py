#!/usr/bin/env python3
"""
Object pooling system for expensive converter and utility instances.

This module provides pooling mechanisms to reuse heavy objects like:
- Converter instances
- Utility parsers (color, transform, unit)
- Processing contexts
"""

import logging
import threading
import time
from collections.abc import Callable
from contextlib import contextmanager
from queue import Empty, Queue
from typing import Any, Dict, Generic, Optional, Type, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar('T')


class ObjectPool(Generic[T]):
    """Generic object pool for reusing expensive instances."""
    
    def __init__(self, 
                 factory: Callable[[], T],
                 max_size: int = 10,
                 init_size: int = 3,
                 max_idle_time: float = 300.0,  # 5 minutes
                 cleanup_interval: float = 60.0):  # 1 minute
        """
        Initialize object pool.
        
        Args:
            factory: Function that creates new instances
            max_size: Maximum pool size
            init_size: Initial number of objects to create
            max_idle_time: Maximum time objects can be idle before cleanup
            cleanup_interval: How often to run cleanup
        """
        self.factory = factory
        self.max_size = max_size
        self.max_idle_time = max_idle_time
        self.cleanup_interval = cleanup_interval
        
        self._pool: Queue[T] = Queue(maxsize=max_size)
        self._pool_times: dict[int, float] = {}  # Track when objects were returned
        self._created_count = 0
        self._borrowed_count = 0
        self._returned_count = 0
        self._lock = threading.RLock()
        
        # Pre-populate pool
        for _ in range(init_size):
            obj = self._create_instance()
            if obj is not None:
                self._pool.put(obj)
        
        # Start cleanup thread
        self._cleanup_thread = threading.Thread(target=self._cleanup_worker, daemon=True)
        self._cleanup_thread.start()
    
    def _create_instance(self) -> T | None:
        """Create a new instance using the factory."""
        try:
            instance = self.factory()
            self._created_count += 1
            logger.debug(f"Created new pool instance (total: {self._created_count})")
            return instance
        except Exception as e:
            logger.error(f"Failed to create pool instance: {e}")
            return None
    
    def borrow(self) -> T | None:
        """Borrow an object from the pool."""
        with self._lock:
            try:
                # Try to get from pool
                obj = self._pool.get_nowait()
                obj_id = id(obj)
                self._pool_times.pop(obj_id, None)
                self._borrowed_count += 1
                logger.debug(f"Borrowed object from pool (borrowed: {self._borrowed_count})")
                return obj
            except Empty:
                # Pool is empty, create new instance if under max size
                if self._created_count < self.max_size:
                    obj = self._create_instance()
                    if obj is not None:
                        self._borrowed_count += 1
                        return obj
                
                # Max size reached, wait for return or create temporary
                logger.warning("Pool exhausted, creating temporary instance")
                return self._create_instance()
    
    def return_object(self, obj: T):
        """Return an object to the pool."""
        if obj is None:
            return
        
        with self._lock:
            try:
                # Reset object state if it has a reset method
                if hasattr(obj, 'reset'):
                    obj.reset()
                
                # Add to pool if there's space
                self._pool.put_nowait(obj)
                self._pool_times[id(obj)] = time.time()
                self._returned_count += 1
                logger.debug(f"Returned object to pool (returned: {self._returned_count})")
                
            except Exception as e:
                logger.warning(f"Failed to return object to pool: {e}")
    
    def _cleanup_worker(self):
        """Background worker to clean up idle objects."""
        while True:
            try:
                time.sleep(self.cleanup_interval)
                self._cleanup_idle_objects()
            except Exception as e:
                logger.error(f"Error in pool cleanup worker: {e}")
    
    def _cleanup_idle_objects(self):
        """Remove objects that have been idle too long."""
        current_time = time.time()
        
        with self._lock:
            objects_to_remove = []
            
            # Check all objects in pool for idle time
            temp_objects = []
            while True:
                try:
                    obj = self._pool.get_nowait()
                    obj_id = id(obj)
                    return_time = self._pool_times.get(obj_id, current_time)
                    
                    if current_time - return_time > self.max_idle_time:
                        # Object is too old, don't return to pool
                        objects_to_remove.append(obj_id)
                        logger.debug(f"Removing idle object from pool")
                    else:
                        # Object is still fresh, keep it
                        temp_objects.append(obj)
                    
                except Empty:
                    break
            
            # Return non-idle objects to pool
            for obj in temp_objects:
                try:
                    self._pool.put_nowait(obj)
                except:
                    pass  # Pool might be full
            
            # Clean up timing records
            for obj_id in objects_to_remove:
                self._pool_times.pop(obj_id, None)
    
    def get_stats(self) -> dict[str, Any]:
        """Get pool statistics."""
        with self._lock:
            return {
                'created_count': self._created_count,
                'borrowed_count': self._borrowed_count,
                'returned_count': self._returned_count,
                'current_pool_size': self._pool.qsize(),
                'max_size': self.max_size,
                'utilization': (self._created_count - self._pool.qsize()) / max(self.max_size, 1),
            }
    
    @contextmanager
    def get_object(self):
        """Context manager for borrowing and automatically returning objects."""
        obj = self.borrow()
        try:
            yield obj
        finally:
            if obj is not None:
                self.return_object(obj)


class UtilityPool:
    """Pool manager for utility classes like parsers and converters."""
    
    def __init__(self):
        self._pools: dict[str, ObjectPool] = {}
        self._lock = threading.RLock()
    
    def register_pool(self, 
                     name: str, 
                     factory: Callable[[], Any],
                     max_size: int = 5,
                     init_size: int = 2) -> ObjectPool:
        """Register a new utility pool."""
        with self._lock:
            if name in self._pools:
                logger.warning(f"Pool '{name}' already exists, overwriting")
            
            pool = ObjectPool(
                factory=factory,
                max_size=max_size,
                init_size=init_size,
            )
            self._pools[name] = pool
            logger.info(f"Registered utility pool '{name}' with max_size={max_size}")
            return pool
    
    def get_pool(self, name: str) -> ObjectPool | None:
        """Get a utility pool by name."""
        with self._lock:
            return self._pools.get(name)
    
    @contextmanager
    def borrow(self, pool_name: str):
        """Borrow an object from a named pool."""
        pool = self.get_pool(pool_name)
        if pool is None:
            raise ValueError(f"Pool '{pool_name}' not found")
        
        with pool.get_object() as obj:
            yield obj
    
    def get_all_stats(self) -> dict[str, dict[str, Any]]:
        """Get statistics for all pools."""
        with self._lock:
            return {name: pool.get_stats() for name, pool in self._pools.items()}


class ConverterPool:
    """Specialized pool for converter instances."""
    
    def __init__(self):
        self.utility_pool = UtilityPool()
        self._converter_pools: dict[type, ObjectPool] = {}
        self._lock = threading.RLock()
        
        # Pre-register common utility pools
        self._register_common_utilities()
    
    def _register_common_utilities(self):
        """Register commonly used utility pools.

        This method is deprecated and maintained for backward compatibility.
        With ConversionServices dependency injection, utility pooling is now
        handled at the service level rather than requiring manual registration.

        All utility creation and pooling is now managed by ConversionServices
        which provides singleton instances and proper lifecycle management.
        """
        # Migrated to ConversionServices - no manual utility registration needed
        # ConversionServices provides centralized dependency injection for all utilities
        pass
    
    def register_converter_pool(self, 
                              converter_class: type,
                              max_size: int = 5,
                              init_size: int = 2) -> ObjectPool:
        """Register a pool for a specific converter class."""
        with self._lock:
            if converter_class in self._converter_pools:
                logger.warning(f"Converter pool for {converter_class.__name__} already exists")
                return self._converter_pools[converter_class]
            
            def factory():
                # Create converter with pooled utilities
                instance = converter_class()
                # Replace utility instances with pooled ones if available
                self._inject_pooled_utilities(instance)
                return instance
            
            pool = ObjectPool(
                factory=factory,
                max_size=max_size,
                init_size=init_size,
            )
            
            self._converter_pools[converter_class] = pool
            logger.info(f"Registered converter pool for {converter_class.__name__}")
            return pool
    
    def _inject_pooled_utilities(self, converter_instance):
        """Inject pooled utilities into converter instance."""
        # This is a simplified injection - in practice, you'd want to
        # modify the converter base class to support utility injection
        utility_mappings = {
            'unit_converter': 'unit_converter',
            'color_parser': 'color_parser', 
            'transform_engine': 'transform_engine',
            'viewport_handler': 'viewport_handler',
        }
        
        for pool_name, attr_name in utility_mappings.items():
            if hasattr(converter_instance, attr_name):
                # Note: This is a simplified approach - in production you'd want
                # to implement a proper dependency injection system
                pass
    
    @contextmanager
    def get_converter(self, converter_class: type):
        """Get a converter instance from the pool."""
        with self._lock:
            if converter_class not in self._converter_pools:
                self.register_converter_pool(converter_class)
            
            pool = self._converter_pools[converter_class]
        
        with pool.get_object() as converter:
            yield converter
    
    @contextmanager
    def get_utility(self, utility_name: str):
        """Get a utility instance from the pool."""
        with self.utility_pool.borrow(utility_name) as utility:
            yield utility
    
    def get_all_stats(self) -> dict[str, Any]:
        """Get statistics for all pools."""
        stats = {
            'utilities': self.utility_pool.get_all_stats(),
            'converters': {},
        }
        
        with self._lock:
            for converter_class, pool in self._converter_pools.items():
                stats['converters'][converter_class.__name__] = pool.get_stats()
        
        return stats


# Global pool instances
_global_utility_pool = None
_global_converter_pool = None

def get_utility_pool() -> UtilityPool:
    """Get or create the global utility pool."""
    global _global_utility_pool
    if _global_utility_pool is None:
        _global_utility_pool = UtilityPool()
    return _global_utility_pool

def get_converter_pool() -> ConverterPool:
    """Get or create the global converter pool.""" 
    global _global_converter_pool
    if _global_converter_pool is None:
        _global_converter_pool = ConverterPool()
    return _global_converter_pool