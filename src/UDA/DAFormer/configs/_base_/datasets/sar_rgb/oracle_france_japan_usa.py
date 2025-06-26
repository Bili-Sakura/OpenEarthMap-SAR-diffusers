# ---------------------------------------------------------------
# Copyright (c) 2021-2022 ETH Zurich, Lukas Hoyer. All rights reserved.
# Licensed under the Apache License, Version 2.0
# ---------------------------------------------------------------

# dataset settings
dataset_type = "OEMSARDataset"  
data_root = "/home/cliffbb/OEM-SAR/dataset"     
img_norm_cfg = dict(
    mean=[46.2651, 123.0489, 126.8835, 113.9639], 
    std=[3.4281,  56.9896, 48.3336, 46.5853], 
    to_rgb=False)
crop_size = (512, 512)

source_train_pipeline = [
    dict(type='LoadImageFromFile', color_type='unchanged'), 
    dict(type='LoadAnnotations'),
    dict(type='Resize', img_scale=(1024, 1024)),
    dict(type='RandomCrop', crop_size=crop_size, cat_max_ratio=0.75),
    dict(type='RandomFlip', prob=0.5),
    # dict(type='PhotoMetricDistortion'),  # is applied later in dacs.py
    dict(type='Normalize', **img_norm_cfg),
    dict(type='Pad', size=crop_size, pad_val=0, seg_pad_val=255),
    dict(type='DefaultFormatBundle'),
    dict(type='Collect', keys=['img', 'gt_semantic_seg']),]

target_train_pipeline = [
    dict(type='LoadImageFromFile', color_type='unchanged'), 
    dict(type='LoadAnnotations'),
    dict(type='Resize', img_scale=(1024, 1024)),
    dict(type='RandomCrop', crop_size=crop_size),
    dict(type='RandomFlip', prob=0.5),
    # dict(type='PhotoMetricDistortion'),  # is applied later in dacs.py
    dict(type='Normalize', **img_norm_cfg),
    dict(type='Pad', size=crop_size, pad_val=0, seg_pad_val=255),
    dict(type='DefaultFormatBundle'),
    dict(type='Collect', keys=['img', 'gt_semantic_seg']),]

test_pipeline = [
    dict(type='LoadImageFromFile', color_type='unchanged'), 
    dict(
        type='MultiScaleFlipAug',
        img_scale=(1024, 1024),
        # MultiScaleFlipAug is disabled by not providing img_ratios
        # and setting flip=False
        # img_ratios=[0.5, 0.75, 1.0, 1.25, 1.5, 1.75],
        flip=False,
        transforms=[
            dict(type='Resize', keep_ratio=True),
            dict(type='RandomFlip'),
            dict(type='Normalize', **img_norm_cfg),
            dict(type='ImageToTensor', keys=['img']),
            dict(type='Collect', keys=['img']),
        ])]

# data = dict(
#     samples_per_gpu=8,
#     workers_per_gpu=1,
#     train=dict(
#         type='OEMSAR_UDADataset',
#         source=dict(# source train set
#             type=dataset_type, 
#             data_root=data_root,  
#             img_dir="sar_rgb_images",  
#             ann_dir="pseudo_real_labels", 
#             split = "uda_splits/train_pseudo_france_japan_source.txt", 
#             pipeline=source_train_pipeline),
#         target=dict(# target train set
#             type=dataset_type, 
#             data_root=data_root,  
#             img_dir="sar_rgb_images",  
#             ann_dir="pseudo_real_labels", 
#             split = "uda_splits/train_pseudo_usa_target.txt", 
#             pipeline=target_train_pipeline)),
#     val=dict(# target val set
#         type=dataset_type,
#         data_root=data_root,
#         img_dir="sar_rgb_images",  
#         ann_dir="pseudo_real_labels", 
#         split = "uda_splits/val_pseudo_usa_target.txt", 
#         pipeline=test_pipeline),
#     test=dict(# target test set
#         type=dataset_type,
#         data_root=data_root,
#         img_dir="sar_images",  
#         ann_dir="real_labels", 
#         split = "uda_splits/test_real_usa_target.txt", 
#         pipeline=test_pipeline)
# )

# Source only data config
data = dict(
    samples_per_gpu=8,
    workers_per_gpu=1,
    train=dict(# train set
        type=dataset_type, 
        data_root=data_root,  
        img_dir="sar_rgb_images",  
        ann_dir="pseudo_real_labels", 
        split = "uda_splits/train_pseudo_france_japan_usa_source_v2.txt", 
        pipeline=source_train_pipeline),
    val=dict(# val set
        type=dataset_type,
        data_root=data_root,
        img_dir="sar_rgb_images",  
        ann_dir="pseudo_real_labels", 
        split = "uda_splits/val_pseudo_france_japan_usa_source.txt", 
        pipeline=test_pipeline),
    test=dict(# target test set
        type=dataset_type,
        data_root=data_root,
        img_dir="sar_rgb_images",  
        ann_dir="real_labels", 
        split = "uda_splits/test_real_usa_target.txt", 
        pipeline=test_pipeline)
)
