"""
JMeter Performance Comparison Engine
Compares JMeter test results between baseline and current runs
"""

from typing import Dict, List, Any, Tuple
import statistics


class JMeterComparisonEngine:
    """
    Compares JMeter metrics and classifies performance changes
    """
    
    # Classification thresholds
    THRESHOLDS = {
        'stable': 5.0,           # < 5% change
        'minor': 15.0,           # 5-15% change
        'major': 30.0,           # 15-30% change
        'critical': 30.0         # > 30% change
    }
    
    # Critical thresholds for specific metrics
    CRITICAL_THRESHOLDS = {
        'error_rate': 5.0,       # >5% error rate increase is critical
        'throughput': 20.0,      # >20% throughput drop is critical
    }
    
    def __init__(self):
        self.results = {
            'regressions': [],
            'improvements': [],
            'stable_metrics': [],
            'new_failures': [],
            'backend_score': 0.0,
            'summary': {}
        }
    
    def compare(self, baseline_metrics: Dict[str, Any], current_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main comparison method
        
        Args:
            baseline_metrics: Metrics from baseline run (from AnalysisResult.metrics)
            current_metrics: Metrics from current run (from AnalysisResult.metrics)
        
        Returns:
            Comprehensive comparison results
        """
        
        # Compare overall metrics
        self._compare_overall_metrics(baseline_metrics, current_metrics)
        
        # Compare per-transaction metrics
        self._compare_transaction_metrics(baseline_metrics, current_metrics)
        
        # Detect new failures
        self._detect_new_failures(baseline_metrics, current_metrics)
        
        # Calculate backend score
        self._calculate_backend_score()
        
        return self.results
    
    def _compare_overall_metrics(self, baseline: Dict, current: Dict):
        """Compare overall performance metrics"""
        
        metrics_to_compare = [
            ('avg_response_time', 'Average Response Time', 'ms', 'lower_is_better'),
            ('p90_response_time', 'P90 Response Time', 'ms', 'lower_is_better'),
            ('p95_response_time', 'P95 Response Time', 'ms', 'lower_is_better'),
            ('p99_response_time', 'P99 Response Time', 'ms', 'lower_is_better'),
            ('throughput', 'Throughput', 'TPS', 'higher_is_better'),
            ('error_rate', 'Error Rate', '%', 'lower_is_better'),
            ('success_rate', 'Success Rate', '%', 'higher_is_better'),
        ]
        
        for metric_key, metric_name, unit, direction in metrics_to_compare:
            baseline_value = self._get_nested_value(baseline, metric_key)
            current_value = self._get_nested_value(current, metric_key)
            
            if baseline_value is not None and current_value is not None:
                comparison = self._compare_metric(
                    metric_name=metric_name,
                    baseline_value=baseline_value,
                    current_value=current_value,
                    unit=unit,
                    direction=direction,
                    transaction_name=None
                )
                
                self._categorize_comparison(comparison)
    
    def _compare_transaction_metrics(self, baseline: Dict, current: Dict):
        """Compare per-transaction/API metrics"""
        
        baseline_transactions = baseline.get('by_label', {})
        current_transactions = current.get('by_label', {})
        
        # Get all unique transaction names
        all_transactions = set(baseline_transactions.keys()) | set(current_transactions.keys())
        
        for transaction in all_transactions:
            baseline_trans = baseline_transactions.get(transaction, {})
            current_trans = current_transactions.get(transaction, {})
            
            # If transaction exists in current but not baseline, it's new
            if transaction not in baseline_transactions:
                self.results['summary'][f'new_transaction_{transaction}'] = {
                    'type': 'new_api',
                    'avg_response_time': current_trans.get('avg_response_time')
                }
                continue
            
            # If transaction exists in baseline but not current, it's removed
            if transaction not in current_transactions:
                self.results['summary'][f'removed_transaction_{transaction}'] = {
                    'type': 'removed_api',
                    'baseline_avg_response_time': baseline_trans.get('avg_response_time')
                }
                continue
            
            # Compare transaction metrics
            trans_metrics = [
                ('avg_response_time', 'Avg Response Time', 'ms', 'lower_is_better'),
                ('p90', 'P90', 'ms', 'lower_is_better'),
                ('p95', 'P95', 'ms', 'lower_is_better'),
                ('error_rate', 'Error Rate', '%', 'lower_is_better'),
                ('throughput', 'Throughput', 'TPS', 'higher_is_better'),
            ]
            
            for metric_key, metric_name, unit, direction in trans_metrics:
                baseline_value = baseline_trans.get(metric_key)
                current_value = current_trans.get(metric_key)
                
                if baseline_value is not None and current_value is not None:
                    comparison = self._compare_metric(
                        metric_name=f"{transaction} - {metric_name}",
                        baseline_value=baseline_value,
                        current_value=current_value,
                        unit=unit,
                        direction=direction,
                        transaction_name=transaction
                    )
                    
                    self._categorize_comparison(comparison)
    
    def _compare_metric(
        self,
        metric_name: str,
        baseline_value: float,
        current_value: float,
        unit: str,
        direction: str,
        transaction_name: str = None
    ) -> Dict[str, Any]:
        """
        Compare a single metric and calculate change percentage
        
        Args:
            metric_name: Name of the metric
            baseline_value: Baseline metric value
            current_value: Current metric value
            unit: Unit of measurement
            direction: 'lower_is_better' or 'higher_is_better'
            transaction_name: Optional transaction/API name
        
        Returns:
            Comparison result dictionary
        """
        
        # Calculate change
        if baseline_value == 0:
            change_percent = 100.0 if current_value > 0 else 0.0
        else:
            change_percent = ((current_value - baseline_value) / baseline_value) * 100
        
        change_absolute = current_value - baseline_value
        
        # Determine if this is regression or improvement
        if direction == 'lower_is_better':
            is_regression = change_percent > 0
        else:  # higher_is_better
            is_regression = change_percent < 0
        
        # Classify severity
        severity = self._classify_severity(
            change_percent=abs(change_percent),
            metric_name=metric_name,
            is_regression=is_regression
        )
        
        return {
            'metric_name': metric_name,
            'transaction_name': transaction_name,
            'baseline_value': baseline_value,
            'current_value': current_value,
            'change_percent': round(change_percent, 2),
            'change_absolute': round(change_absolute, 2),
            'unit': unit,
            'severity': severity,
            'is_regression': is_regression,
            'direction': direction
        }
    
    def _classify_severity(self, change_percent: float, metric_name: str, is_regression: bool) -> str:
        """
        Classify the severity of a change
        
        Returns: 'stable', 'minor', 'major', or 'critical'
        """
        
        if not is_regression:
            # It's an improvement
            return 'improvement'
        
        # Check for critical metrics with special thresholds
        for critical_metric, threshold in self.CRITICAL_THRESHOLDS.items():
            if critical_metric.lower() in metric_name.lower():
                if change_percent > threshold:
                    return 'critical'
        
        # Apply standard thresholds
        if change_percent < self.THRESHOLDS['stable']:
            return 'stable'
        elif change_percent < self.THRESHOLDS['minor']:
            return 'minor'
        elif change_percent < self.THRESHOLDS['major']:
            return 'major'
        else:
            return 'critical'
    
    def _categorize_comparison(self, comparison: Dict[str, Any]):
        """Categorize comparison into appropriate result bucket"""
        
        severity = comparison['severity']
        is_regression = comparison['is_regression']
        
        if severity == 'improvement' or not is_regression:
            self.results['improvements'].append(comparison)
        elif severity == 'stable':
            self.results['stable_metrics'].append(comparison)
        else:
            self.results['regressions'].append(comparison)
    
    def _detect_new_failures(self, baseline: Dict, current: Dict):
        """Detect new failed transactions"""
        
        baseline_transactions = baseline.get('by_label', {})
        current_transactions = current.get('by_label', {})
        
        for transaction, current_data in current_transactions.items():
            baseline_data = baseline_transactions.get(transaction, {})
            
            baseline_error_rate = baseline_data.get('error_rate', 0)
            current_error_rate = current_data.get('error_rate', 0)
            
            # New failure: error rate went from 0% to >0%
            if baseline_error_rate == 0 and current_error_rate > 0:
                self.results['new_failures'].append({
                    'transaction_name': transaction,
                    'error_rate': current_error_rate,
                    'error_count': current_data.get('error_count', 0),
                    'severity': 'critical'
                })
            # Significant error rate increase
            elif baseline_error_rate > 0 and current_error_rate > baseline_error_rate:
                error_increase_percent = ((current_error_rate - baseline_error_rate) / baseline_error_rate) * 100
                if error_increase_percent > 50:  # >50% increase in errors
                    self.results['new_failures'].append({
                        'transaction_name': transaction,
                        'baseline_error_rate': baseline_error_rate,
                        'current_error_rate': current_error_rate,
                        'increase_percent': round(error_increase_percent, 2),
                        'severity': 'critical'
                    })
    
    def _calculate_backend_score(self):
        """
        Calculate overall backend performance score (0-100)
        Higher is better
        """
        
        # Count metrics by severity
        critical_count = len([r for r in self.results['regressions'] if r['severity'] == 'critical'])
        major_count = len([r for r in self.results['regressions'] if r['severity'] == 'major'])
        minor_count = len([r for r in self.results['regressions'] if r['severity'] == 'minor'])
        improvement_count = len(self.results['improvements'])
        stable_count = len(self.results['stable_metrics'])
        new_failure_count = len(self.results['new_failures'])
        
        total_comparisons = (critical_count + major_count + minor_count + 
                           improvement_count + stable_count)
        
        if total_comparisons == 0:
            self.results['backend_score'] = 100.0
            return
        
        # Penalty scoring
        penalties = 0
        penalties += critical_count * 20  # -20 points per critical regression
        penalties += major_count * 10     # -10 points per major regression
        penalties += minor_count * 5      # -5 points per minor regression
        penalties += new_failure_count * 25  # -25 points per new failure
        
        # Bonus for improvements
        bonuses = improvement_count * 3  # +3 points per improvement
        
        # Start from 100 and apply penalties/bonuses
        score = 100 - penalties + bonuses
        
        # Clamp to 0-100
        self.results['backend_score'] = max(0.0, min(100.0, score))
        
        # Store summary
        self.results['summary']['total_comparisons'] = total_comparisons
        self.results['summary']['critical_regressions'] = critical_count
        self.results['summary']['major_regressions'] = major_count
        self.results['summary']['minor_regressions'] = minor_count
        self.results['summary']['improvements'] = improvement_count
        self.results['summary']['stable_metrics'] = stable_count
        self.results['summary']['new_failures'] = new_failure_count
    
    def _get_nested_value(self, data: Dict, key: str) -> Any:
        """
        Get value from nested dictionary using dot notation
        e.g., 'response_time.avg' -> data['response_time']['avg']
        """
        keys = key.split('.')
        value = data
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return None
        return value
    
    def get_top_regressions(self, limit: int = 10) -> List[Dict]:
        """Get top N worst regressions sorted by severity and change %"""
        
        # Sort: critical first, then by change percent
        severity_order = {'critical': 0, 'major': 1, 'minor': 2}
        
        sorted_regressions = sorted(
            self.results['regressions'],
            key=lambda x: (severity_order.get(x['severity'], 3), -abs(x['change_percent']))
        )
        
        return sorted_regressions[:limit]
    
    def get_slowest_transactions(self) -> List[Dict]:
        """Get transactions with highest response times"""
        
        slowest = [
            r for r in self.results['regressions']
            if 'Response Time' in r['metric_name'] and r['transaction_name']
        ]
        
        return sorted(slowest, key=lambda x: x['current_value'], reverse=True)[:10]
