"""Configuration validator to prevent accidental changes to critical settings."""
import logging
from pathlib import Path
import tomli
import tomli_w

logger = logging.getLogger(__name__)

CRITICAL_SETTINGS = {
    'streamlit': {
        'port': 5000,
        'address': '0.0.0.0'
    },
    'fastapi': {
        'port': 5002,
        'address': '0.0.0.0'
    }
}

def validate_streamlit_config():
    """Validate Streamlit configuration."""
    config_path = Path('.streamlit/config.toml')
    try:
        with open(config_path, 'rb') as f:
            config = tomli.load(f)
        
        server_config = config.get('server', {})
        if server_config.get('port') != CRITICAL_SETTINGS['streamlit']['port']:
            logger.error("❌ CRITICAL: Streamlit port has been modified from required value 5000!")
            return False
        
        if server_config.get('address') != CRITICAL_SETTINGS['streamlit']['address']:
            logger.error("❌ CRITICAL: Streamlit address has been modified from required value '0.0.0.0'!")
            return False
            
        return True
    except Exception as e:
        logger.error(f"Error validating Streamlit config: {str(e)}")
        return False

def validate_replit_config():
    """Validate Replit configuration."""
    replit_path = Path('.replit')
    try:
        with open(replit_path, 'rb') as f:
            config = tomli.load(f)
        
        # Check workflow configurations
        workflows = config.get('workflows', {}).get('workflow', [])
        for workflow in workflows:
            if workflow.get('name') == 'Streamlit App':
                tasks = workflow.get('tasks', [])
                for task in tasks:
                    if task.get('task') == 'shell.exec':
                        if '5000' not in task.get('args', ''):
                            logger.error("❌ CRITICAL: Streamlit port in workflow config doesn't match required value 5000!")
                            return False
            elif workflow.get('name') == 'Reddit Analyzer API':
                tasks = workflow.get('tasks', [])
                for task in tasks:
                    if task.get('task') == 'shell.exec':
                        if '5002' not in task.get('args', ''):
                            logger.error("❌ CRITICAL: FastAPI port in workflow config doesn't match required value 5002!")
                            return False
        return True
    except Exception as e:
        logger.error(f"Error validating Replit config: {str(e)}")
        return False

def validate_all_configs():
    """Validate all critical configurations."""
    streamlit_valid = validate_streamlit_config()
    replit_valid = validate_replit_config()
    
    if not (streamlit_valid and replit_valid):
        logger.error("⚠️ Configuration validation failed! System may be unstable.")
        return False
        
    logger.info("✅ All configurations validated successfully.")
    return True
