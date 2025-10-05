#!/usr/bin/env python3
"""
Performance profiling and monitoring for SVG conversion operations.

This module provides detailed performance tracking, bottleneck identification,
and optimization recommendations for the conversion pipeline.
"""

import cProfile
import gc
import io
import json
import logging
import pstats
import threading
import time
from collections import defaultdict, deque
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import dataclass, field
from functools import wraps
from typing import Any, Dict, List, Optional

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    psutil = None

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetric:
    """Individual performance measurement."""
    name: str
    start_time: float
    end_time: float
    duration: float
    memory_before: int
    memory_after: int
    memory_delta: int
    cpu_percent: float
    thread_id: int
    metadata: dict[str, Any] = field(default_factory=dict)
    
    @property
    def memory_mb(self) -> float:
        """Memory usage in MB."""
        return self.memory_delta / (1024 * 1024)


@dataclass
class ProfileSession:
    """A profiling session with aggregated metrics."""
    session_id: str
    start_time: float
    end_time: float | None = None
    metrics: list[PerformanceMetric] = field(default_factory=list)
    total_memory_peak: int = 0
    total_duration: float = 0.0
    
    def add_metric(self, metric: PerformanceMetric):
        """Add a metric to the session."""
        self.metrics.append(metric)
        self.total_memory_peak = max(self.total_memory_peak, metric.memory_after)
    
    def finalize(self):
        """Finalize the session."""
        if self.end_time is None:
            self.end_time = time.time()
            self.total_duration = self.end_time - self.start_time
    
    def get_summary(self) -> dict[str, Any]:
        """Get session summary statistics."""
        if not self.metrics:
            return {'error': 'No metrics recorded'}
        
        durations = [m.duration for m in self.metrics]
        memory_deltas = [m.memory_delta for m in self.metrics]
        
        return {
            'session_id': self.session_id,
            'total_duration': self.total_duration,
            'metric_count': len(self.metrics),
            'avg_operation_time': sum(durations) / len(durations),
            'max_operation_time': max(durations),
            'min_operation_time': min(durations),
            'total_memory_allocated': sum(memory_deltas),
            'peak_memory_usage': self.total_memory_peak,
            'operations_per_second': len(self.metrics) / max(self.total_duration, 0.001),
        }


class PerformanceProfiler:
    """Main performance profiler for SVG conversion operations."""
    
    def __init__(self, 
                 max_sessions: int = 100,
                 max_metrics_per_session: int = 1000,
                 auto_gc: bool = True,
                 profile_memory: bool = True,
                 profile_cpu: bool = True):
        """
        Initialize the performance profiler.
        
        Args:
            max_sessions: Maximum number of sessions to keep in memory
            max_metrics_per_session: Maximum metrics per session
            auto_gc: Whether to automatically run garbage collection
            profile_memory: Whether to track memory usage
            profile_cpu: Whether to track CPU usage
        """
        self.max_sessions = max_sessions
        self.max_metrics_per_session = max_metrics_per_session
        self.auto_gc = auto_gc
        self.profile_memory = profile_memory
        self.profile_cpu = profile_cpu
        
        self.sessions: dict[str, ProfileSession] = {}
        self.current_session: ProfileSession | None = None
        self.operation_stack: list[dict[str, Any]] = []
        
        # Thread safety
        self.lock = threading.RLock()
        
        # Aggregated statistics
        self.operation_stats: dict[str, list[float]] = defaultdict(list)
        self.bottleneck_history: deque = deque(maxlen=100)
        
        # CPU profiler
        self.cpu_profiler: cProfile.Profile | None = None
        
        # Memory tracking
        if self.profile_memory and PSUTIL_AVAILABLE:
            self.process = psutil.Process()
        else:
            self.process = None
    
    def start_session(self, session_id: str) -> ProfileSession:
        """Start a new profiling session."""
        with self.lock:
            if self.current_session and self.current_session.end_time is None:
                logger.warning(f"Ending previous session {self.current_session.session_id}")
                self.current_session.finalize()
            
            session = ProfileSession(
                session_id=session_id,
                start_time=time.time(),
            )
            
            self.sessions[session_id] = session
            self.current_session = session
            
            # Clean up old sessions if needed
            if len(self.sessions) > self.max_sessions:
                oldest_id = min(self.sessions.keys(), 
                              key=lambda k: self.sessions[k].start_time)
                del self.sessions[oldest_id]
            
            logger.info(f"Started profiling session: {session_id}")
            return session
    
    def end_session(self, session_id: str | None = None):
        """End a profiling session."""
        with self.lock:
            if session_id is None:
                session = self.current_session
            else:
                session = self.sessions.get(session_id)
            
            if session and session.end_time is None:
                session.finalize()
                logger.info(f"Ended profiling session: {session.session_id} "
                          f"({session.total_duration:.3f}s, {len(session.metrics)} metrics)")
                
                if session == self.current_session:
                    self.current_session = None
    
    @contextmanager
    def profile_operation(self, 
                         operation_name: str,
                         metadata: dict[str, Any] | None = None):
        """Context manager for profiling individual operations."""
        # Prepare measurement
        start_time = time.time()
        memory_before = 0
        cpu_percent_start = 0
        
        if self.profile_memory and self.process:
            memory_before = self.process.memory_info().rss

        if self.profile_cpu and self.process:
            cpu_percent_start = self.process.cpu_percent()
        
        # Track operation start
        operation_context = {
            'name': operation_name,
            'start_time': start_time,
            'memory_before': memory_before,
            'cpu_percent_start': cpu_percent_start,
            'thread_id': threading.get_ident(),
            'metadata': metadata or {},
        }
        
        with self.lock:
            self.operation_stack.append(operation_context)
        
        try:
            yield operation_context
            
        finally:
            # Measure completion
            end_time = time.time()
            duration = end_time - start_time
            
            memory_after = 0
            cpu_percent = 0
            
            if self.profile_memory and self.process:
                memory_after = self.process.memory_info().rss

            if self.profile_cpu and self.process:
                # Get CPU percentage since start of operation
                cpu_percent = self.process.cpu_percent()
            
            # Create metric
            metric = PerformanceMetric(
                name=operation_name,
                start_time=start_time,
                end_time=end_time,
                duration=duration,
                memory_before=memory_before,
                memory_after=memory_after,
                memory_delta=memory_after - memory_before,
                cpu_percent=cpu_percent,
                thread_id=threading.get_ident(),
                metadata=metadata or {},
            )
            
            # Record metric
            with self.lock:
                if self.current_session:
                    if len(self.current_session.metrics) < self.max_metrics_per_session:
                        self.current_session.add_metric(metric)
                
                # Update operation statistics
                self.operation_stats[operation_name].append(duration)
                
                # Keep only recent measurements
                if len(self.operation_stats[operation_name]) > 1000:
                    self.operation_stats[operation_name] = \
                        self.operation_stats[operation_name][-500:]
                
                # Remove from stack
                if self.operation_stack and self.operation_stack[-1] == operation_context:
                    self.operation_stack.pop()
                
                # Check for bottlenecks
                if duration > 0.1:  # Operations slower than 100ms
                    self.bottleneck_history.append({
                        'operation': operation_name,
                        'duration': duration,
                        'timestamp': end_time,
                        'memory_delta': memory_after - memory_before,
                        'metadata': metadata,
                    })
            
            # Auto garbage collection for memory-intensive operations
            if self.auto_gc and memory_after - memory_before > 50 * 1024 * 1024:  # 50MB
                logger.debug(f"Running GC after {operation_name} (allocated {(memory_after - memory_before) / 1024 / 1024:.1f}MB)")
                gc.collect()
    
    def profile_function(self, 
                        operation_name: str | None = None,
                        include_args: bool = False):
        """Decorator for profiling functions."""
        def decorator(func: Callable) -> Callable:
            name = operation_name or f"{func.__module__}.{func.__name__}"
            
            @wraps(func)
            def wrapper(*args, **kwargs):
                metadata = {}
                if include_args:
                    metadata.update({
                        'args_count': len(args),
                        'kwargs_count': len(kwargs),
                        'args_types': [type(arg).__name__ for arg in args[:5]],  # First 5 only
                    })
                
                with self.profile_operation(name, metadata):
                    return func(*args, **kwargs)
            
            return wrapper
        return decorator
    
    def start_cpu_profiling(self):
        """Start detailed CPU profiling."""
        if self.cpu_profiler is None:
            self.cpu_profiler = cProfile.Profile()
            self.cpu_profiler.enable()
            logger.info("Started CPU profiling")
    
    def stop_cpu_profiling(self) -> str:
        """Stop CPU profiling and return results."""
        if self.cpu_profiler is None:
            return "No CPU profiling session active"
        
        self.cpu_profiler.disable()
        
        # Capture profiling results
        s = io.StringIO()
        stats = pstats.Stats(self.cpu_profiler, stream=s)
        stats.sort_stats('cumulative')
        stats.print_stats(50)  # Top 50 functions
        
        result = s.getvalue()
        self.cpu_profiler = None
        
        logger.info("Stopped CPU profiling")
        return result
    
    def get_session_report(self, session_id: str) -> dict[str, Any]:
        """Get detailed report for a session."""
        with self.lock:
            session = self.sessions.get(session_id)
            if not session:
                return {'error': f'Session {session_id} not found'}
            
            # Basic summary
            report = session.get_summary()
            
            # Operation breakdown
            operation_breakdown = defaultdict(list)
            for metric in session.metrics:
                operation_breakdown[metric.name].append({
                    'duration': metric.duration,
                    'memory_delta': metric.memory_delta,
                    'cpu_percent': metric.cpu_percent,
                })
            
            # Top operations by time
            operation_totals = {}
            for op_name, metrics in operation_breakdown.items():
                total_time = sum(m['duration'] for m in metrics)
                total_memory = sum(m['memory_delta'] for m in metrics)
                avg_cpu = sum(m['cpu_percent'] for m in metrics) / len(metrics)
                
                operation_totals[op_name] = {
                    'total_time': total_time,
                    'total_memory': total_memory,
                    'avg_cpu': avg_cpu,
                    'call_count': len(metrics),
                    'avg_time': total_time / len(metrics),
                }
            
            # Sort by total time
            top_operations = sorted(
                operation_totals.items(),
                key=lambda x: x[1]['total_time'],
                reverse=True,
            )[:20]
            
            report.update({
                'operation_breakdown': dict(top_operations),
                'bottlenecks': [b for b in self.bottleneck_history 
                              if b['timestamp'] >= session.start_time and 
                                 (session.end_time is None or b['timestamp'] <= session.end_time)],
                'memory_peak_mb': session.total_memory_peak / (1024 * 1024),
            })
            
            return report
    
    def get_global_stats(self) -> dict[str, Any]:
        """Get global performance statistics."""
        with self.lock:
            # Overall operation statistics
            operation_stats = {}
            for op_name, durations in self.operation_stats.items():
                if durations:
                    operation_stats[op_name] = {
                        'call_count': len(durations),
                        'total_time': sum(durations),
                        'avg_time': sum(durations) / len(durations),
                        'min_time': min(durations),
                        'max_time': max(durations),
                        'p95_time': sorted(durations)[int(len(durations) * 0.95)] if len(durations) >= 20 else max(durations),
                    }
            
            # Recent bottlenecks
            recent_bottlenecks = list(self.bottleneck_history)[-20:]
            
            # Memory usage
            current_memory = 0
            if self.profile_memory and self.process:
                current_memory = self.process.memory_info().rss / (1024 * 1024)  # MB
            
            return {
                'active_sessions': len([s for s in self.sessions.values() if s.end_time is None]),
                'total_sessions': len(self.sessions),
                'operation_stats': operation_stats,
                'recent_bottlenecks': recent_bottlenecks,
                'current_memory_mb': current_memory,
                'profiler_config': {
                    'max_sessions': self.max_sessions,
                    'max_metrics_per_session': self.max_metrics_per_session,
                    'auto_gc': self.auto_gc,
                    'profile_memory': self.profile_memory,
                    'profile_cpu': self.profile_cpu,
                },
            }
    
    def export_session(self, session_id: str, filepath: str):
        """Export session data to JSON file."""
        report = self.get_session_report(session_id)
        
        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        logger.info(f"Exported session {session_id} to {filepath}")
    
    def clear_old_data(self, max_age_hours: float = 24):
        """Clear old profiling data."""
        cutoff_time = time.time() - (max_age_hours * 3600)
        
        with self.lock:
            # Remove old sessions
            old_sessions = [
                session_id for session_id, session in self.sessions.items()
                if session.start_time < cutoff_time
            ]
            
            for session_id in old_sessions:
                del self.sessions[session_id]
            
            # Clear old operation stats
            for op_name in list(self.operation_stats.keys()):
                self.operation_stats[op_name] = [
                    duration for duration in self.operation_stats[op_name][-500:]
                ]
                
                if not self.operation_stats[op_name]:
                    del self.operation_stats[op_name]
            
            # Clear old bottleneck history
            recent_bottlenecks = [
                b for b in self.bottleneck_history
                if b['timestamp'] > cutoff_time
            ]
            self.bottleneck_history.clear()
            self.bottleneck_history.extend(recent_bottlenecks)
            
            logger.info(f"Cleared {len(old_sessions)} old sessions and old statistics")
    
    def get_optimization_recommendations(self) -> list[str]:
        """Get optimization recommendations based on profiling data."""
        recommendations = []
        
        with self.lock:
            # Analyze bottlenecks
            if self.bottleneck_history:
                bottleneck_operations = defaultdict(int)
                total_bottleneck_time = 0
                
                for bottleneck in self.bottleneck_history:
                    bottleneck_operations[bottleneck['operation']] += 1
                    total_bottleneck_time += bottleneck['duration']
                
                # Most problematic operations
                top_bottlenecks = sorted(
                    bottleneck_operations.items(),
                    key=lambda x: x[1],
                    reverse=True,
                )[:5]
                
                for operation, count in top_bottlenecks:
                    recommendations.append(
                        f"Operation '{operation}' caused {count} bottlenecks - consider optimization",
                    )
            
            # Memory usage recommendations
            high_memory_ops = []
            for bottleneck in self.bottleneck_history:
                if bottleneck.get('memory_delta', 0) > 100 * 1024 * 1024:  # 100MB
                    high_memory_ops.append(bottleneck['operation'])
            
            if high_memory_ops:
                unique_ops = list(set(high_memory_ops))
                recommendations.append(
                    f"High memory usage detected in: {', '.join(unique_ops[:3])} - consider memory optimization",
                )
            
            # Performance pattern analysis
            for op_name, durations in self.operation_stats.items():
                if len(durations) >= 10:
                    avg_time = sum(durations) / len(durations)
                    max_time = max(durations)
                    
                    if max_time > avg_time * 5:  # High variance
                        recommendations.append(
                            f"Operation '{op_name}' has high variance ({max_time:.3f}s max vs {avg_time:.3f}s avg) - investigate inconsistent performance",
                        )
            
            # Caching recommendations
            frequently_called = [
                (op_name, len(durations)) 
                for op_name, durations in self.operation_stats.items()
                if len(durations) > 100
            ]
            
            if frequently_called:
                recommendations.append(
                    "Consider caching for frequently called operations: " + 
                    ', '.join([f"{op} ({count} calls)" for op, count in frequently_called[:3]]),
                )
        
        return recommendations


# Global profiler instance
_global_profiler = None

def get_profiler() -> PerformanceProfiler:
    """Get or create the global performance profiler."""
    global _global_profiler
    if _global_profiler is None:
        _global_profiler = PerformanceProfiler()
    return _global_profiler