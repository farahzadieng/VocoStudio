import unittest

from webapp.model_catalog import get_model_spec, get_tool_spec


class ModelCatalogTests(unittest.TestCase):
    def test_enhancement_exposes_three_friendly_models(self):
        tool = get_tool_spec("enhancement")
        self.assertEqual(tool.task, "speech_enhancement")
        self.assertEqual(tool.model_names, (
            "FRCRN_SE_16K", "MossFormerGAN_SE_16K", "MossFormer2_SE_48K"
        ))
        self.assertEqual(get_model_spec("FRCRN_SE_16K").label_fa, "مدل سریع و سبک")

    def test_separation_is_fixed_to_two_speaker_model(self):
        tool = get_tool_spec("separation")
        self.assertEqual(tool.model_names, ("MossFormer2_SS_16K",))
        self.assertEqual(tool.output_kind, "multi_audio")

    def test_all_six_models_have_matching_checkpoint_names(self):
        names = {
            "FRCRN_SE_16K", "MossFormerGAN_SE_16K", "MossFormer2_SE_48K",
            "MossFormer2_SS_16K", "MossFormer2_SR_48K", "AV_MossFormer2_TSE_16K",
        }
        self.assertEqual({get_model_spec(name).checkpoint_dir for name in names}, names)

    def test_unknown_model_is_rejected(self):
        with self.assertRaises(KeyError):
            get_model_spec("unknown")
