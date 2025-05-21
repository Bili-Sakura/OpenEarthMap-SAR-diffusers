<div align="justify">
	
## OpenEarthMap Synthetic Aperture Radar Dataset 
[normal link](https://www.google.com/)
<p align="justify">
This repository contains baseline models for <a href="https://arxiv.org/abs/2501.10891v2" style="text-decoration: none;">OpenEarthMap Synthetic Aperture Radar</a> (OpenEarthMap-SAR) benchmark dataset for land cover mapping under all-weather conditions. The motivation of this benchmark dataset is to facilitate advancements in SAR-based geospatial analysis for global high-resolution land cover mapping. 
<a href="https://www.google.com/" style="color: red; text-decoration: none;text-decoration-style: dotted;">custom link</a>
</p> 
<p><img src="docs/examples-min.png"></p>
</div>

<div align="center">
	
[![GitHub license](https://badgen.net/github/license/Naereen/Strapdown.js)](https://github.com/Naereen/StrapDown.js/blob/master/LICENSE)
<a href="https://pytorch.org/get-started/locally/"><img alt="PyTorch" src="https://img.shields.io/badge/PyTorch-ee4c2c?logo=pytorch&logoColor=white"></a>
![Python](https://img.shields.io/badge/python-3.9+-blue.svg)
</div>

 
<!--## Context
<div align="justify">

This repository contains the baseline models for the OpenEarthMap-SAR land cover mapping generalized few-shot semantic segmentation challenge. 
The motivation is to enable researchers to develop and benchmark learning methods for generalized few-shot semantic segmentation of high-resolution remote sensing imagery. 
The challenge is in two phases: the development phase is for developing and testing methods on a *valset*, and the evaluation phase is for tweaking and testing on a *testset* for final submission.

The pre-trained models with different SSL methods are provided as follows (13 bands of S2-L1C, 100 epochs, input clip to [0,1] by dividing 10000).
</div>-->

## Dataset
<div align="justify">

<p>	
The <a href="https://arxiv.org/abs/2501.10891v2">OpenEarthMap Synthetic Aperture Radar</a> (OpenEarthMap-SAR) is a SAR dataset for global high-resolution land cover mapping under all weather conditions. The dataset consists of 1.5 million segments of 5033 aerial and satellite images with some manually annotated and all having pseudo land cover labels of 8 classes, covering 35 regions from Japan, France, and the USA. Each image has a size of 1024x1024 pixels at a ground sampling distance of 0.15m--0.5m. The dataset has served as the official dataset for 2025 IEEE GRSS Data Fusion Contest Track I. The dataset has been made publicly available at <a href="https://zenodo.org/records/14622048">Zenodo</a>.


The dataset for the Track 1 challenge is OpenEarthMap-SAR. The OpenEarthMap-SAR is a synthetic aperture radar dataset benchmark with OpenEarthMap optical data for global high-resolution land cover mapping. It consists of 5033 images at a 0.15–0.5m ground sampling distance covering 35 regions from Japan, France and the USA; and with partially manually annotated labels and fully pseudo labels of 8 land cover classes. A detailed description of the dataset can be found here, where it can also be downloaded. Below are examples of the OpenEarthMap-SAR dataset.


</p>
<!--<p><img src="docs/assets/img/fewshot-examples1.png"></p>-->
</div>

## Baseline
<div align="justify">
<!--The pre-trained models with different SSL methods are provided as follows (13 bands of S2-L1C, 100 epochs, input clip to [0,1] by dividing 10000).-->
The PSPNet architecture with EfficientNet-B4 encoder from the [Segmentation Models Pytorch](https://github.com/qubvel/segmentation_models.pytorch?tab=readme-ov-file) GitHub repository is adopted as a baseline network.
The network was pretrained using the *trainset* with the [Catalyst](https://catalyst-team.com/) library. Then, the state-of-the-art framework called [distilled information maximization](https://arxiv.org/abs/2211.14126) 
(DIaM) was adopted to perform the GFSS task. The code in this repository contains only the GFSS portion. As mentioned by the baseline authors, any pretrained model can be used with their framework. 
The code was adopted from [here](https://github.com/sinahmr/DIaM?tab=readme-ov-file). To run the code on the *valset*, simply clone this repository and change your directory into the `OEM-Fewshot-Challenge` folder which contains the code files. Then from a terminal, run the `test.sh` script. as:
```bash
bash test.sh 
```
The results of the baseline model on the *valset* are presented below. To reproduce the results, download the pretrained models from [here](https://drive.google.com/file/d/1eLjfUJ2ajAMkJKCsoJr-MGSSzZ-LqDbR/view?usp=sharing). 
Follow the instructions in the **Usage** section, then run the `test.sh` script as explained. 

<table align="center">
    <tr align="center">
        <td>Phase</td>
        <td>base mIoU</td> 
	<td>novel mIoU</td> 
	<td>Average base-novel mIoU</td>
        <td>Weighted base mIoU</td> 
	<td>Weighted novel mIoU</td>
	<td>Weighted-Sum base-novel mIoU</td>
    </tr>
    <tr align="center">
        <td>valset</td>
        <td> 29.48 </td> 
	<td> 03.18 </td> 
	<td> 16.33 </td> 
	<td> 11.79 </td> 
	<td> 1.91 </td> 
	<td> 13.70 </td> 
    </tr>
   <tr align="center">
	<td>testset</td>
        <td> --- </td> 
	<td> --- </td> 
	<td> --- </td> 
	<td> --- </td> 
	<td> --- </td> 
	<td> --- </td> 
    </tr>   
</table>
The weighted mIoUs are calculated using `0.4:0.6 => base:novel`. These weights are derived from the state-of-the-art results presented in the baseline paper.

</div>

## Usage
<div align="justify">

The repository structure consists of a configuration file that can be found in `config/`; data splits for each set in `data/`; and  all the codes for the GFSS task are in `src/`. The testing script `test.sh` is at the root of the repo.
The `docs` folder contains only GitHub page files.

To use the baseline code, you first need to clone the repository and change your directory into the `OEM-Fewshot-Challenge` folder. Then follow the steps below:</br>
1. Install all the requirements. `Python 3.9` was used in our experiments. Install the list of packages in the `requirements.txt` file using `pip install -r requirements.txt`.
2. Download the dataset from [here](https://zenodo.org/records/10591939) into a directory that you set in the config file `oem.yaml`
3. Download the pretrained weights from [here](https://drive.google.com/file/d/1eLjfUJ2ajAMkJKCsoJr-MGSSzZ-LqDbR/view?usp=sharing) into a directory that you set in the config file `oem.yaml`
4. In the `oem.yaml` you need to set only the paths for the dataset and the pretrained weights. The other settings need not be changed to reproduce the results.
5. Test the model by running the `test.sh` script as mentioned in the **Baseline** section. The script will use the *support_set* to adapt and predict the segmentation maps of the *query_set*. After running the script, the results are provided in a `results` folder which contains a `.txt` file of the IoUs and mIoUs, and a `preds` and `targets` folder for the predicted and the targets maps, respectively.

You can pretrained your model using the *trainset* and any simple training scheme of your choice. The baseline paper used the [`train_base.py`](https://github.com/chunbolang/BAM/blob/main/train_base.py) script and base learner models of [BAM](https://github.com/chunbolang/BAM) (see the [baseline paper](https://github.com/sinahmr/DIaM?tab=readme-ov-file) for more info).
 
</div>

## Citation
<div align="justify">
For any scientific publication using this data, the following paper should be cited:
<pre style="white-space: pre-wrap; white-space: -moz-pre-wrap; white-space: -pre-wrap; white-space: -o-pre-wrap; word-wrap: break-word;">
@InProceedings{Xia_2023_WACV,
    author    = {Xia, Junshi and Yokoya, Naoto and Adriano, Bruno and Broni-Bediako, Clifford},
    title     = {OpenEarthMap: A Benchmark Dataset for Global High-Resolution Land Cover Mapping},
    booktitle = {Proceedings of the IEEE/CVF Winter Conference on Applications of Computer Vision (WACV)},
    month     = {January},
    year      = {2023},
    pages     = {6254-6264}
}
</pre>
</div>

## Acknowledgements
<div align="justify">

We are most grateful to the authors of [DIaM](https://github.com/sinahmr/DIaM?tab=readme-ov-file), [Semantic Segmentation PyTorch](https://github.com/qubvel/segmentation_models.pytorch?tab=readme-ov-file), 
and [Catalyst](https://catalyst-team.com/) from which the baseline code is built on.
</div>
