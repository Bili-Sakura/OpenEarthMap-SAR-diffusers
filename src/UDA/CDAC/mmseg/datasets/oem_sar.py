from .builder import DATASETS
from .custom import CustomDataset

import os.path as osp


@DATASETS.register_module()
class OEMSARDataset(CustomDataset):
    """OpenEarthMap dataset
    ``img_suffix`` and ``seg_map_suffix`` are set to ".tif" 
    """
    CLASSES = ("void class", "bareland", "rangeland", "developed space", "road", 
                "tree", "water", "agriculture land", "buildings")

    PALETTE = [[0, 0, 0], [128, 0, 0], [0, 255, 36], [148, 148, 148], [255, 255, 255],
               [34, 97, 38], [0, 69, 255], [75, 181, 73], [222, 31, 7]]
    
    def __init__(self, **kwargs):
        super(OEMSARDataset, self).__init__(img_suffix="", 
                                        seg_map_suffix="",
                                        # reduce_zero_label=False,
                                        **kwargs)
        
        assert osp.exists(self.img_dir) and osp.exists(self.ann_dir) and self.split is not None
