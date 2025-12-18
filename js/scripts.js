import { app } from "../../scripts/app.js";
app.registerExtension({ 
	name: "DigbyWanVACEVideoSmooth",
	async setup() { 
    },
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeType.comfyClass=="DigbyWanVACEVideoSmooth") {
       		const onConnectionsChange = nodeType.prototype.onConnectionsChange;
    		nodeType.prototype.onConnectionsChange = function (side,slot,connect,link_info,slot_info) {     
	    		const r = onConnectionsChange?.apply(this, arguments);   
                if ((side == 1) && (slot_info.name == "video2")) {
                    console.log("ok, i got the matching slot")
                    var disable_transition_center = ((link_info != null) && (connect)) 
                    this.widgets[1].disabled = disable_transition_center
                }

                return r;
            }
        }
    }
})

app.registerExtension({ 
	name: "DigbyWan22SmoothVideoTransition",
	async setup() { 
    },
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeType.comfyClass=="DigbyWan22SmoothVideoTransition") {
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