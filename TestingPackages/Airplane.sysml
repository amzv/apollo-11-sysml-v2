package AirplanePackage {
	private import ISQ::*;
	private import SI::*;

	// Port and Connection definitions
	port def FuelPort;
	port def ControlPort;

	interface def FuelInterface {
		end source : FuelPort;
		end destination : FuelPort;
	}

	interface def ControlInterface {
		end controller : ControlPort;
		end receiver : ControlPort;
	}

	part def Fuselage {
		port cockpitControl : ControlPort;
	}

	part def Wing {
		port fuelTank : FuelPort;
	}

	part def Engine {
		port fuelIn : FuelPort;
		port controlIn : ControlPort;
	}

	part def Tail {
		port controlIn : ControlPort;
	}

	part def Airplane {
		part fuselage : Fuselage;
		part leftWing : Wing;
		part rightWing : Wing;
		part leftEngine : Engine;
		part rightEngine : Engine;
		part tail : Tail;

		// Connections representing mounting and fluid/signal flows
		interface leftFuelLine : FuelInterface connect leftWing.fuelTank to leftEngine.fuelIn;
		interface rightFuelLine : FuelInterface connect rightWing.fuelTank to rightEngine.fuelIn;

		interface leftEngineControl : ControlInterface connect fuselage.cockpitControl to leftEngine.controlIn;
		interface rightEngineControl : ControlInterface connect fuselage.cockpitControl to rightEngine.controlIn;
		interface tailControl : ControlInterface connect fuselage.cockpitControl to tail.controlIn;
	}
}
