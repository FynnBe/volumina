import numpy as np
import warnings
from collections import defaultdict
from itertools import izip

try:
    _pandas_available = True
    import pandas as pd
except ImportError:
    _pandas_available = False
    warnings.warn("pandas not available. edge_coords functions will be slower.")

def edge_coords_along_axis( label_img, axis ):
    """
    Find the edges between label segments along a particular axis, e.g. if axis=-1
    Return all edges as keys in a dict, along with the list of coordinates that belong to the edge.
    
    Returns a dict of edges -> coordinate lists
    That is: { (id1, id2) : [coord, coord, coord, coord...] }
    
    Where:
        - id1 is always less than id2
        - for each 'coord', len(coord) == label_img.ndim
        - the edge lies just to the RIGHT (or down, or whatever) of the coordinate
    """
    if axis < 0:
        axis += label_img.ndim
    assert label_img.ndim > axis
    if label_img.shape[axis] == 1:
        return {} # No edges
    
    up_slicing = ((slice(None),) * axis) + (np.s_[:-1],)
    down_slicing = ((slice(None),) * axis) + (np.s_[1:],)

    edge_mask = (label_img[up_slicing] != label_img[down_slicing])
    
    # Instead of using .transpose() here (which induces a copy),
    # we use use a clever little trick: The arrays in the index
    # tuple have a common base, and it's exactly what we want.
    #edge_coords = np.transpose(np.nonzero(edge_mask))
    edge_coords = np.nonzero(edge_mask)[0].base
    assert edge_coords.shape[1] == label_img.ndim

    edge_ids = np.ndarray(shape=(len(edge_coords), 2), dtype=np.uint32 )
    edge_ids[:, 0] = label_img[up_slicing][edge_mask]
    edge_ids[:, 1] = label_img[down_slicing][edge_mask]
    edge_ids.sort(axis=1)

    # pandas can do groupby 3x faster than pure-python,
    # but pure-python is faster on tiny data (e.g. a couple 256*256 tiles)
    if _pandas_available and len(edge_ids) > 10000:
        df = pd.DataFrame({ 'id1' : edge_ids[:,0],
                            'id2' : edge_ids[:,1],
                            'coords' : NpIter(edge_coords) }) # This is much faster than list(edge_coords)
        return df.groupby(['id1', 'id2'])['coords'].apply(np.asarray).to_dict()
    else:
        grouped_coords = defaultdict(list)
        for id_pair, coords in izip( edge_ids, edge_coords ):
            grouped_coords[tuple(id_pair)].append(coords)
        return grouped_coords

class NpIter(object):
    # This class just exists because we don't want to copy edge_coords,
    # but iter() objects don't support __len__, which pandas needs.
    def __init__(self, a):
        self.iter = iter(a)
        self._len = len(a)

    def __next__(self):
        return self.iter.__next__()

    def __len__(self):
        return self._len

def edge_coords_2d( label_img ):
    vertical_edge_coords = edge_coords_along_axis( label_img, 0 )
    horizontal_edge_coords = edge_coords_along_axis( label_img, 1 )
    return (vertical_edge_coords, horizontal_edge_coords)

def edge_coords_nd( label_img, axes=None ):
    if axes is None:
        axes = range(label_img.ndim)
    result = []    
    for axis in axes:
        result.append( edge_coords_along_axis(label_img, axis) )
    return result

if __name__ == "__main__":
    import h5py
    watershed_path = '/magnetic/data/flyem/chris-two-stage-ilps/volumes/subvol/watershed-512.h5'
    with h5py.File(watershed_path, 'r') as f:
        watershed = f['watershed'][:256, :256, :256]

    from lazyflow.utility import Timer
    with Timer() as timer:
        edge_coords_nd(watershed)
    print "Time was: {}".format( timer.seconds() )

#     labels_img = np.load('/Users/bergs/workspace/ilastik-meta/ilastik/seg-slice-256.npy')
#     assert labels_img.dtype == np.uint32
#
#     vert_edges, horizontal_edges = edge_coords_nd(labels_img)
#     for id_pair, coords_list in horizontal_edges.iteritems():
#         print id_pair, ":", coords_list
