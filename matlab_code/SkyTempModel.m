function [TskyEst] = SkyTempModel(x,K,Ta,DewPoint)%,Tsky)
%TskyEst,Esky,DLREst] = the other model uses these outputs
if ~isequal(length(K),length(DewPoint),length(Ta))
    error('SkyTempModel: input vectors not of equal length\n');
end

%A = 94;
%B = 12.6;
%C = 13;
%D = 0.314;

%Vapor pressure (Pa) via Tetens equation
Pw = 6.1078.*exp((17.27.*(DewPoint))./((DewPoint)+237.3));

TskyEst = x(1) + x(2).*log(Pw) - x(3).*K + x(4).*(Ta+273.15);
%{
if (flag)
    A(5) = 1;
else
    A(5) = 0.5;
end
TskyEst = DryBulb + (A(1).*(DryBulb - (DewPoint+273.15)) + A(2));

Esky = 1-(1+W./10).*exp(-1.*(A(3) + A(4).*W./10).^A(5));

DLREst = (5.67*10^(-8))*Esky.*TskyEst.^4;
%}
%E1 = mean((TskyEst - Tsky').^2);
%fprintf('RMS Error Sky: %4.5f\n',E1);
%E2 = sqrt(mean((DLREst - (5.67*10^(-8)).*Tsky.^4).^2));
%fprintf('RMS Error Rad: %4.6f\n',E2);

return;
end