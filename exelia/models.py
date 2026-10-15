"""Stage model recommendations, deliberately separate from actual model routing."""
from .common import ROOT, load, utc

STAGES = {
    'discovery': {'effort': 'medium', 'reason': 'Structured requirements analysis'},
    'architecture': {'effort': 'high', 'reason': 'Cross-system constraints and security tradeoffs'},
    'implementation': {'effort': 'medium', 'reason': 'Routine code delivery, raise effort for uncertainty'},
    'debugging': {'effort': 'high', 'reason': 'Uncertain root-cause investigation'},
    'review': {'effort': 'high', 'reason': 'Independent defect and security assessment'},
    'docs': {'effort': 'low', 'reason': 'Clear, bounded documentation work'},
    'qa': {'effort': 'medium', 'reason': 'Reproducible test generation and evidence review'},
}

def recommend(root=ROOT, stage='implementation', risk='normal'):
    if stage not in STAGES:
        raise ValueError('Unknown stage')
    if risk not in ('low', 'normal', 'high'):
        raise ValueError('Risk must be low/normal/high')
    config = load(root / 'project.config.json', {})
    effort = STAGES[stage]['effort']
    if risk == 'high':
        effort = 'high'
    if risk == 'low' and stage not in ('architecture', 'review'):
        effort = 'low'
    return {'generated_at': utc(), 'stage': stage, 'risk': risk, 'suggested_model': 'current configured Codex model',
            'suggested_reasoning_effort': effort, 'rationale': STAGES[stage]['reason'],
            'actual_model_routing_verified': False,
            'note': 'A recommendation only. Verify effective model in Codex before claiming a switch.',
            'conversation_language': config.get('conversation_language')}
