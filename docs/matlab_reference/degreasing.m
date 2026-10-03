
%% Simulation for degreasing process
% For: Jose Daniel Hernandez Betancur
% Mater thesis title: "Detection of the critcal points of hot-dip galvanizing process:
% a focus on sustainability and sustainable development
% Master degree's name: Master in Engineering - Materials and Processes
% University: National University of Colombia - Medellin branch
% Date: 03 October, 2017
%%-----------------------------------------------------------------------------------------------------------


function [m_saponified,m_remaining_grease,Q1,m_sln,C,Tsln,m_sln_remove] = ...
degreasing(m_grease_and_oil,MW_grease,m_sln_o,Co,Tslno,m_steel_greased,Qo,Tamb)

% Mass balance

m_saponified = 0.7*m_grease_and_oil;
m_remaining_grease = 0.3*m_grease_and_oil;

rho = density(Tslno,Co(1),1);
MW_RCOO = MW_grease - 41.0716;

m_sln_remove = 1e-6*m_steel_greased*rho;
m_NaOH = 0.01*Co(1)*(m_sln_o - m_sln_remove) - m_saponified*38.9971*3/MW_grease;
m_H2O = 0.01*Co(2)*(m_sln_o - m_sln_remove);
m_grycerol = 0.01*Co(3)*(m_sln_o - m_sln_remove) + m_saponified*92.0937/MW_grease;
m_sodium_carboxylates = 0.01*Co(4)*(m_sln_o - m_sln_remove) + m_saponified*(MW_RCOO + 68.9694)/MW_grease;

m_sln = m_NaOH + m_H2O + m_grycerol + m_sodium_carboxylates;
C = [m_NaOH m_H2O m_grycerol m_sodium_carboxylates]*(100/m_sln);

% Energy balance

Cpo = -627.6*(Co(1) - 1.08)/16.73 + 4121.2;
Cpf = -627.6*(C(1) - 1.08)/16.73 + 4121.2;
lost = abs((Tslno - Tamb)/35.1);

num = (1 - 0.1*lost)*m_sln*Cpo*(Tslno - 25) + 25*m_sln*Cpf + Tamb*m_steel_greased*450 + Qo;
den = m_sln*Cpf + m_steel_greased*450;
Tsln = num/den;

Q1 = 0.1*lost*m_sln*Cpo*(Tslno - 25) + m_steel_greased*450*(Tsln - Tamb);

return
