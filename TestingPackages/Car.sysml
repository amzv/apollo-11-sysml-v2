package CarPackage {
	part def Car {
		part engine : Engine;
		part transmission : Transmission;
		part wheels[4] : Wheel;
		part chassis : Chassis;
	}

	part def Engine;
	part def Transmission;
	part def Wheel;
	part def Chassis;
}

package CarRequirementsPackage {
	private import ISQ::*;
	private import SI::*;
	private import ModelingMetadata::*;

	requirement def <'REQ-001'> AutonomousDrivingRequirement {
		doc /* The vehicle shall perform autonomous driving operations equivalent to SAE Level 3, including lane keeping, adaptive cruise control, and collision avoidance. */
		@Rationale {
			text = "To provide autonomous capability without requiring a fully dedicated human driver at all times.";
		}
	}

	requirement def <'REQ-002'> SensorCostRequirement {
		doc /* The total bill of materials (BOM) cost of the autonomous sensor suite (cameras, radar, LiDAR) shall not exceed $1500 USD. */
		@Rationale {
			text = "To ensure the vehicle remains affordable as an economy hatchback.";
		}
	}

	requirement def <'REQ-003'> HatchbackUtilityRequirement {
		doc /* The vehicle shall have a 5-door hatchback configuration with a minimum cargo volume of 350 liters. */
		@Rationale {
			text = "To maintain the utility and compact footprint expected of a hatchback.";
		}
	}

	requirement def <'REQ-004'> ElectricRangeRequirement {
		doc /* The electric powertrain shall provide a minimum driving range of 400 [km] on a single full charge. */
		@Rationale {
			text = "To ensure practical daily usability for consumers.";
		}
	}
}
