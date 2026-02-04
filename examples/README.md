# DroneForge AI - Example Configurations

This folder contains example mission configurations for different drone use cases.

## Usage

Run any example using the batch mode:

```bash
python main.py --config examples/agricultural_sprayer.json
python main.py --config examples/photography_drone.json
python main.py --config examples/survey_fixed_wing.json
```

## Examples

### 1. Agricultural Sprayer (`agricultural_sprayer.json`)
- **Type**: Hexacopter
- **Payload**: 15L liquid (15kg)
- **Flight Time**: 20+ minutes
- **Features**: Autonomous waypoints, GPS navigation, dust/water resistance
- **Regulation**: India DGCA
- **Budget**: ~$3000

### 2. Photography Drone (`photography_drone.json`)
- **Type**: Quadcopter
- **Payload**: 300g gimbal camera
- **Flight Time**: 25+ minutes
- **Features**: Smooth flight, orbit mode, follow-me
- **Regulation**: USA FAA
- **Budget**: ~$1500

### 3. Survey Fixed-Wing (`survey_fixed_wing.json`)
- **Type**: Fixed-wing aircraft
- **Payload**: 400g multispectral camera
- **Flight Time**: 60+ minutes
- **Features**: Hand-launch, belly-landing, survey patterns
- **Regulation**: EU EASA
- **Budget**: ~€4000

## Custom Configuration

Create your own configuration file with the following structure:

```json
{
    "mission": "Your detailed mission description here...",
    "provider": "ollama",           // or "openai", "anthropic", "google"
    "model": "llama3",              // Model name for your provider
    "cad_detail": "basic",          // "basic" or "detailed"
    "jurisdictions": ["india_dgca"], // List of regulatory jurisdictions
    "output_dir": "./output/my_drone"
}
```

### Mission Statement Tips

For best results, include in your mission statement:
- **Payload**: Type, weight, dimensions
- **Performance**: Flight time, range, speed
- **Environment**: Temperature range, weather conditions
- **Autonomy**: Waypoints, obstacle avoidance, RTH
- **Regulatory**: Country/region of operation
- **Budget**: Approximate budget in your currency
- **Special Features**: Any specific requirements

Example:
> "Design a quadcopter for industrial pipeline inspection. Must carry a 500g thermal camera plus 200g RGB camera, fly for 35 minutes, operate in winds up to 10m/s, navigate autonomously along GPS waypoints, avoid obstacles using LiDAR, and comply with FAA Part 107 rules. Budget is $5000. Need IP54 rating for light rain operation."
