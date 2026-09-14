class SpeechModel:
    def get_free_gpu(self):
        try:
            return 0
        except Exception as e:
            print(f"Error finding free GPU: {e}")
            return None

    def download_model(self, model_name):
        checkpoint_dir = self.args.checkpoint_dir
        from huggingface_hub import snapshot_download
        if not os.path.exists(checkpoint_dir):
            os.makedirs(checkpoint_dir)
        print(f'downloading checkpoint for {model_name}')
        try:
            snapshot_download(repo_id=f'alibabasglab/{model_name}', local_dir=checkpoint_dir)
            return True
        except:
            return False
            
    def load_model(self):
        """
        Loads a local model.
        """
        best_name = os.path.join(self.args.checkpoint_dir, 'last_best_checkpoint')
        # Check if the last best checkpoint exists
        if not os.path.isfile(best_name):
            if not self.download_model(self.name):
                # If downloading is unsuccessful
                print(f'Warning: Downloading model {self.name} is not successful. Please try again or manually download from https://huggingface.co/alibabasglab/{self.name}/tree/main !')
                return

        if isinstance(self.model, nn.ModuleList):
            with open(best_name, 'r') as f:
                pass
