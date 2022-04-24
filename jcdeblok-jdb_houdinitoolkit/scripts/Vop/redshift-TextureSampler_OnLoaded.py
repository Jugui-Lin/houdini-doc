import ProAces
#reload(ProAces)
kwargs['node'].addEventCallback((hou.nodeEventType.ParmTupleChanged,), ProAces.UpdateEventHandler)
 