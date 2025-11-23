import { app } from "../../scripts/app.js";
app.registerExtension({ 
	name: "WanVACEVideoSmoother",
	async setup() { 
		console.log("WanVACEVideoSmoother setup complete")
    },
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeType.comfyClass=="WanVACEVideoSmoother") {
       		const onConnectionsChange = nodeType.prototype.onConnectionsChange;
    		nodeType.prototype.onConnectionsChange = function (side,slot,connect,link_info,slot_info) {     
	    		const r = onConnectionsChange?.apply(this, arguments);   
                if ((side == 1) && (slot_info.name == "video2")) {
                    var disable_transition_center = ((link_info != null) && (connect)) 
                    this.widgets[1].disabled = disable_transition_center
                }

                return r;
            }
        }
    }
})

app.registerExtension({ 
	name: "Wan22SmoothVideoTransition",
	async setup() { 
		console.log("Wan22SmoothVideoTransition setup complete")
    },
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeType.comfyClass=="Wan22SmoothVideoTransition") {
       		const onConnectionsChange = nodeType.prototype.onConnectionsChange;
    		nodeType.prototype.onConnectionsChange = function (side,slot,connect,link_info,slot_info) {     
	    		const r = onConnectionsChange?.apply(this, arguments);   
                if ((side == 1) && (slot_info.name == "video2")) {
                    var disable_transition_center = ((link_info != null) && (connect)) 
                    this.widgets[4].disabled = disable_transition_center
                }

                return r;
            }
        }
    }
})