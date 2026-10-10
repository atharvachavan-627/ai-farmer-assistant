import { useState } from 'react';
import { Eye, EyeOff } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import TextField from './TextField';

export default function PasswordField(props) {
  const { t } = useTranslation();
  const [visible, setVisible] = useState(false);
  return (
    <TextField {...props} type={visible ? 'text' : 'password'}>
      <button
        type="button"
        className="field__toggle"
        onClick={() => setVisible((v) => !v)}
        aria-label={visible ? t('common.hidePassword') : t('common.showPassword')}
        aria-pressed={visible}
      >
        {visible ? <EyeOff size={18} aria-hidden="true" /> : <Eye size={18} aria-hidden="true" />}
      </button>
    </TextField>
  );
}
